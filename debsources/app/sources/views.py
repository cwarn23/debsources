import os
from functools import partial

from flask import request, current_app, render_template, redirect, url_for
from debian.debian_support import version_compare

from debsources import statistics
from debsources.utils import (
        path_join, extract_stats, get_packages_prefixes, local_info)
from debsources.consts import SLOCCOUNT_LANGUAGES
from debsources.app import app_wrapper
from debsources.exceptions import (
    InvalidPackageOrVersionError, FileOrFolderNotFound)
from debsources.db import query as q

from ..app.views import GeneralView, ErrorHandler
from ..app.exceptions import HTTP404Error
from ..app import forms
from ..app.helper import Location, Directory, SourceFile

from . import bp_sources
from .infobox import Infobox


session = app_wrapper.session


@bp_sources.context_processor
def skeleton_variables():
    site_name = bp_sources.name

    # TODO oops, heavy disk I/O, move it in memory!
    _update_ts_file = path_join(current_app.config['cache_dir'], 'last-update')
    last_update = local_info.read_update_ts(_update_ts_file)

    packages_prefixes = get_packages_prefixes(
        current_app.config['cache_dir'])

    # credits_file = os.path.join(app.config["LOCAL_DIR"], "credits.html")
    # credits = local_info.read_html(credits_file)

    # return dict(packages_prefixes=packages_prefixes,
    #             searchform=SearchForm(),
    #             last_update=last_update,
    #             credits=credits)
    return dict(site_name=site_name,
                packages_prefixes=packages_prefixes,
                search_form=forms.SearchForm(),
                last_update=last_update,
                )

# site errors
# XXX 500 handler cannot be registered on a blueprint
bp_sources.errorhandler(403)(
        lambda e: (ErrorHandler(bp_name='sources')(e, http=403), 403))
bp_sources.errorhandler(404)(
        lambda e: (ErrorHandler(bp_name='sources')(e, http=404), 404))


class StatsView(GeneralView):

    def get_stats_suite(self, suite, **kwargs):
        if suite not in statistics.suites(session, 'all'):
            raise HTTP404Error()  # security, to avoid suite='../../foo',
            # to include <img>s, etc.
        # XXX it's no longer stats.data, it's now sources_stats.data
        stats_file = path_join(current_app.config["cache_dir"], "sources_stats.data")
        res = extract_stats(filename=stats_file,
                            filter_suites=["debian_" + suite])

        return dict(results=res,
                    languages=SLOCCOUNT_LANGUAGES,
                    suite=suite)

    def get_stats(self):
        stats_file = path_join(current_app.config["cache_dir"], "sources_stats.data")
        res = extract_stats(filename=stats_file)

        all_suites = ["debian_" + x for x in
                      statistics.suites(session, suites='all')]
        release_suites = ["debian_" + x for x in
                          statistics.suites(session, suites='release')]
        devel_suites = ["debian_" + x for x in
                        statistics.suites(session, suites='devel')]

        return dict(results=res,
                    languages=SLOCCOUNT_LANGUAGES,
                    all_suites=all_suites,
                    release_suites=release_suites,
                    devel_suites=devel_suites)


class SourceView(GeneralView):

    def get_package(self, package):
        """
        renders the package page (which lists available versions)
        """
        suite = request.args.get("suite") or ""
        suite = suite.lower()
        if suite == "all":
            suite = ""
        # we list the version with suites it belongs to
        try:
            versions_w_suites = q.pkg_versions_w_suites(
                session, package, suite)
        except InvalidPackageOrVersionError:
            raise HTTP404Error("%s not found" % package)

        # we [re]bind the render_func
        self.render_func = partial(
            render_template,
            'sources/source_package.html',)

        return dict(type="package",
                    package=package,
                    versions=versions_w_suites,
                    suite=suite,)

    def get_location(self, package, loc_path):
        loc_dict = loc_path.split('/')
        version, path = loc_dict[0], '/'.join(loc_dict[1:])

        if version == "latest":  # we search the latest available version
            return self.get_latest_version(package, path)
        else:
            try:
                location = Location(session,
                                    current_app.config["sources_dir"],
                                    current_app.config["sources_static"],
                                    package, version, path)
            except (FileOrFolderNotFound, InvalidPackageOrVersionError):
                raise HTTP404ErrorSuggestions(package, version, path)

            if location.is_symlink():
                # check if it's secure
                symlink_dest = os.readlink(location.sources_path)
                dest = os.path.normpath(  # absolute, target file
                    os.path.join(os.path.dirname(location.sources_path),
                                symlink_dest))
                # note: adding trailing slash because normpath drops them
                if dest.startswith(os.path.normpath(location.version_path) + '/'):
                    # symlink is safe; redirect to its destination
                    # XXX redirect
                    redirect_url = os.path.normpath(
                        os.path.join(os.path.dirname(location.path_to),
                        symlink_dest))
                    self.render_func = partial(redirect, redirect_url)
                    return {}
                else:
                    raise HTTP403Error(
                        'insecure symlink, pointing outside package/version/')

            if location.is_dir():  # folder, we list its content
                return self._render_directory(location)

            elif location.is_file():  # file
                return self._render_file(location)

            else:  # doesn't exist
                raise HTTP404Error(None)

            return {}

    def _render_directory(self, location):
        """
        renders a directory, lists subdirs and subfiles
        """
        directory = Directory(location, toplevel=(location.get_path() == ""))

        # (if path == "", then the dir is toplevel, and we don't want
        # the .pc directory)

        pkg_infos = Infobox(session,
                            location.get_package(),
                            location.get_version()).get_infos()

        # XXX again, set render_func
        self.render_func = partial(
            render_template,
            'sources/source_folder.html',
            subdirs=filter(lambda x: x['type'] == "directory", kwargs['content']),
            subfiles=filter(lambda x: x['type'] == "file", kwargs['content']),
            pathl=Location.get_path_links(".source_location", kwargs['path']),)

        return dict(type="directory",
                    directory=location.get_deepest_element(),
                    package=location.get_package(),
                    content=directory.get_listing(),
                    path=location.get_path_to(),
                    pkg_infos=pkg_infos,
                    )

    def _render_file(self, location):
        """
        renders a file
        """
        file_ = SourceFile(location)

        checksum = file_.get_sha256sum(session)
        number_of_duplicates = (session.query(sql_func.count(Checksum.id))
                                .filter(Checksum.sha256 == checksum)
                                .first()[0])

        pkg_infos = Infobox(session,
                            location.get_package(),
                            location.get_version()).get_infos()

        return dict(type="file",
                    file=location.get_deepest_element(),
                    package=location.get_package(),
                    mime=file_.get_mime(),
                    raw_url=file_.get_raw_url(),
                    path=location.get_path_to(),
                    text_file=file_.istextfile(),
                    stat=location.get_stat(location.sources_path),
                    checksum=checksum,
                    number_of_duplicates=number_of_duplicates,
                    pkg_infos=pkg_infos
                    )

    def get_latest_version(self, package, path):
        """
        redirects to the latest version for the requested page,
        when 'latest' is provided instead of a version number
        """
        try:
            versions = q.pkg_versions(session, package)
        except InvalidPackageOrVersionError:
            raise HTTT404Error("%s not found" % package)
        # the latest version is the latest item in the
        # sorted list (by debian_support.version_compare)
        version = sorted([v.version for v in versions],
                         cmp=version_compare)[-1]

        # avoids extra '/' at the end
        if path == "":
            location = version
        else:
            location = '/'.join(version, path)

        # finally we tell the render function to redirect
        self.render_func = partial(
            redirect,
            url_for('.source_location', package=package, location=location))
        return dict()

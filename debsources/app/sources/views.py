from flask import request, current_app

from debsources import statistics
from debsources.utils import (
        path_join, extract_stats, get_packages_prefixes, local_info)
from debsources.consts import SLOCCOUNT_LANGUAGES
from debsources.app import app_wrapper

from ..app.views import GeneralView, ErrorHandler
from ..app.exceptions import HTTP404Error
from ..app import forms

from . import bp_sources


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
    """
    TODO
    """

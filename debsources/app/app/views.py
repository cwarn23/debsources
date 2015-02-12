# Copyright (C) 2013-2014  Matthieu Caneill <matthieu.caneill@gmail.com>
#
# This file is part of Debsources.
#
# Debsources is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from flask import (redirect, url_for, request, current_app, render_template,
                   jsonify)
from flask.views import View

from debsources.utils import local_info, path_join, get_packages_prefixes
from debsources.app import app_wrapper
from debsources.db import query as q
from debsources.db import models
from debsources.consts import SUITES

from .helper import format_big_num, Pagination

from . import forms
from .exceptions import (HTTP403Error, HTTP404Error, HTTP500Error,
                         HTTP404ErrorSuggestions)

app = app_wrapper.app
session = app_wrapper.session


# Jinja2 environment helpers

app.jinja_env.filters['format_big_num'] = format_big_num


# ERRORS
class ErrorHandler(object):

    def __init__(self, bp_name='', mode='html'):
        self.mode = mode
        self.bp_name = bp_name

    def __call__(self, error, http=404):
        try:
            method = getattr(self, 'error_{}'.format(http))
        except:
            raise Exception("Unimplemented HTTP error: {}".format(http))
        return method(error)

    def error_403(self, error):
        if self.mode == 'json':
            return jsonify(dict(error=403))
        else:
            return render_template(path_join(self.bp_name, '403.html')), 403

    def error_404(self, error):
        if self.mode == 'json':
            return jsonify(dict(error=404))
        else:
            if isinstance(error, HTTP404ErrorSuggestions):
                # let's suggest all the possible locations with a different
                # package version
                possible_versions = q.pkg_versions(session, error.package)
                suggestions = ['/'.join(
                    filter(None, [error.package, v.version, error.path]))
                    for v in possible_versions]
                return render_template(
                    path_join(self.bp_name, '404_suggestions.html'),
                    suggestions=suggestions), 404
            else:
                return render_template(
                    path_join(self.bp_name, '404.html')), 404

    def error_500(self, error):
        """
        logs a 500 error and returns the correct template
        """
        app.logger.exception(error)

        if self.mode == 'json':
            return jsonify(dict(error=500))
        else:
            return render_template(
                path_join(self.bp_name, '500.html')), 500


app.errorhandler(403)(lambda _: ("Forbidden", 403))
app.errorhandler(404)(lambda _: ("File not Found", 404))
app.errorhandler(500)(lambda _: ("Server Error", 500))


# for both rendering and api
class GeneralView(View):
    def __init__(self,
                 render_func=jsonify,
                 err_func=lambda *args, **kwargs: "OOPS! Error occurred.",
                 get_objects=None,
                 **kwargs):
        """
        render_func: the render function, e.g. jsonify or render_template
        err_func: the function called when an error occurs
        get_objects: the function called to get context objects.
        """
        self.render_func = render_func
        self.err_func = err_func

        if get_objects:
            if isinstance(get_objects, basestring):
                self.get_objects = getattr(self, "get_"+get_objects)
            else:
                # we don't check if it's a callable.
                # if err, then let it err.
                self.get_objects = get_objects

        self.d = kwargs

    def get_objects(self, **kwargs):
        return dict()

    def dispatch_request(self, **kwargs):
        """
        renders the view, or call the error function with the error and
        the http error code (404 or 500)
        """
        try:
            context = self.get_objects(**kwargs)
            return self.render_func(**context)
        except HTTP404Error as e:
            return self.err_func(e, http=404)
        except HTTP403Error as e:
            return self.err_func(e, http=403)
        except HTTP500Error as e:
            return self.err_func(e, http=500)
        # # 500 as final resolution
        # except Exception as e:
        #     return self.err_func(e, http=500)
        # XXX for debug, we comment it.


# for '/'
class IndexView(GeneralView):

    def get_objects(self, **kwargs):
        news_file = path_join(current_app.config["local_dir"],
                              self.d['news_html'])
        news = local_info.read_html(news_file)
        return dict(news=news)


# for /docs/*
class DocView(GeneralView):
    """
    Renders page for /doc/*
    """


# for /about/
class AboutView(GeneralView):
    """
    Renders page for /about/
    """


# for /prefix/*
class PrefixView(GeneralView):

    def get_objects(self, prefix='a'):
        """
        returns the packages beginning with prefix
        and belonging to suite if specified.
        """
        prefix = prefix.lower()
        suite = request.args.get("suite") or ""
        suite = suite.lower()
        if suite == "all":
            suite = ""
        if prefix in get_packages_prefixes(app.config["cache_dir"]):
            try:
                packages = q.pkg_prefixes(session, prefix=prefix, suite=suite)
            except Exception as e:
                raise HTTP500Error(e)

            packages = [p.to_dict() for p in packages]
            return dict(packages=packages,
                        prefix=prefix,
                        suite=suite)
        else:
            raise HTTP404Error("prefix unknown: {}".format(prefix))


# for /list/*
class ListPackagesView(GeneralView):

    def get_objects(self, page=1):
        if self.d.get('api'):  # we retrieve all packages
            try:
                packages = (session.query(models.PackageName)
                            .order_by(models.PackageName.name)
                            .all()
                            )
                packages = [p.to_dict() for p in packages]
                return dict(packages=packages)
            except Exception as e:
                raise HTTP500Error(e)
        else:  # we paginate
            # WARNING: not serializable (TODO: serialize Pagination obj)
            try:
                offset = int(current_app.config.get("list_offset") or 60)

                # we calculate the range of results
                start = (page - 1) * offset
                end = start + offset

                count_packages = (session.query(models.PackageName)
                                  .count()
                                  )
                packages = (session.query(models.PackageName)
                            .order_by(models.PackageName.name)
                            .slice(start, end)
                            )
                pagination = Pagination(page, offset, count_packages)

                return dict(packages=packages,
                            page=page,
                            pagination=pagination)

            except Exception as e:
                raise Http500Error(e)


class SearchView(GeneralView):

    def dispatch_request(self, **kwargs):
        if self.d.get('recv_search'):
            return self.recv_search()
        else:
            return super(SearchView, self).dispatch_request(**kwargs)

    def get_query(self, query=''):
        """
        processes the search query and renders the results in a dict
        """
        query = query.replace('%', '').replace('_', '')
        suite = request.args.get("suite") or ""
        suite = suite.lower()
        if suite == "all":
            suite = ""

        try:
            exact_matching, other_results = q.search_query(
                session, query, suite)
        except Exception as e:
            raise HTTP500Error(e)  # db problem, ...

        if exact_matching is not None:
            exact_matching = exact_matching.to_dict()
        if other_results is not None:
            other_results = [o.to_dict() for o in other_results]
            # we exclude the 'exact' matching from other_results:
            other_results = filter(lambda x: x != exact_matching,
                                   other_results)

        results = dict(exact=exact_matching,
                       other=other_results)
        return dict(results=results, query=query, suite=suite)

    def get_advanced(self):
        return dict(suites_list=SUITES["all"])

    # for '/search/'
    def recv_search(self, **kwargs):
        search_form = forms.SearchForm(request.form)
        if search_form.validate_on_submit():
            params = dict(query=search_form.query.data)
            suite = search_form.suite.data
            if suite:
                params["suite"] = suite
            return redirect(url_for('.search', **params))
        else:
            # we return the form, to display the errors
            return self.render_func(search_form=search_form)


class ChecksumView(GeneralView):

    def get_objects(self, **kwargs):
        """
        Returns the files whose checksum corresponds to the one given.
        """
        try:
            page = int(request.args.get("page"))
        except:
            page = 1
        checksum = request.args.get("checksum")
        package = request.args.get("package") or None

        count = q.checksum_count(session, checksum, package)

        # pagination:
        if self.d.get('pagination'):
            offset = int(current_app.config.get("LIST_OFFSET") or 60)
            start = (page - 1) * offset
            end = start + offset
            slice_ = (start, end)
            pagination = Pagination(page, offset, count)
        else:
            pagination = None
            slice_ = None

        # finally we get the files list
        results = q.files_with_sum(
            session, checksum, slice_=slice_, package=package)

        return dict(results=results,
                    sha256=checksum,
                    count=count,
                    page=page,
                    pagination=pagination)


class CtagView(GeneralView):

    def get_objects(self):
        """
        Returns the places where ctag are found.
        (limit to package if package is not None)
        """
        try:
            page = int(request.args.get("page"))
        except:
            page = 1
        ctag = request.args.get("ctag")
        package = request.args.get("package") or None

        # pagination:
        if self.d.get('pagination'):
            try:
                offset = current_app.config.get("list_offset")
            except:
                offset = 60
            start = (page - 1) * offset
            end = start + offset
            slice_ = (start, end)
        else:
            pagination = None
            slice_ = None

        count, results = q.find_ctag(session, ctag, slice_=slice_,
                                       package=package)
        if self.d.get('pagination'):
            pagination = Pagination(page, offset, count)
        else:
            pagination = None

        return dict(results=results,
                    ctag=ctag,
                    count=count,
                    page=page,
                    package=package,
                    pagination=pagination)

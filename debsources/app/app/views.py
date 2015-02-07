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

from functools import partial

from flask import (redirect, url_for, request, current_app, render_template,
                   jsonify)
from flask.views import View

from debsources.utils import local_info, path_join, get_endp

from . import forms

# ERRORS
def deal_error(error, http=404, mode='html'):
    """ spreads the error in the right place (404 or 500) """
    if http == 404:
        return deal_404_error(error, mode)
    elif http == 500:
        return deal_500_error(error, mode)
    elif http == 403:
        return deal_403_error(error, mode)
    else:
        raise Exception("Unimplemented HTTP error: %s" % str(http))


def deal_404_error(error, mode='html'):
    if mode == 'json':
        return jsonify(dict(error=404))
    else:
        pass
        # TODO
        # if isinstance(error, HTTP404ErrorSuggestions):
            # let's suggest all the possible locations with a different
            # package version
            # possible_versions = PackageName.list_versions(
            #     session, error.package)
            # suggestions = ['/'.join(filter(None,
            #                         [error.package, v.version, error.path]))
            #                for v in possible_versions]
            # return render_template('404_suggestions.html',
            #                        suggestions=suggestions), 404
        # else:
            # return render_template('404.html'), 404


# @app.errorhandler(404)
def page_not_found(e):
    return deal_404_error(e)


def deal_500_error(error, mode='html'):
    """ logs a 500 error and returns the correct template """
    app.logger.exception(error)

    if mode == 'json':
        return jsonify(dict(error=500))
    else:
        return render_template('500.html'), 500


# @app.errorhandler(500)
def server_error(e):
    return deal_500_error(e)


def deal_403_error(error, mode='html'):
    if mode == 'json':
        return jsonify(dict(error=403))
    else:
        return render_template('403.html'), 403


# @app.errorhandler(403)  # NOQA
def server_error(e):
    return deal_403_error(e)


# for both rendering and api
class GeneralView(View):
    def __init__(self,
                 tpl_name=None,
                 render_func=render_template,
                 err_func=deal_error,
                 get_objects=None,
                 **kwargs):
        """
        render_func: the render function, e.g. jsonify or render_template
        err_func: the function called when an error occurs
        get_objects: the function called to get context objects.
        """
        if isinstance(render_func, basestring):
            self.render_func = getattr(self, render_func)
        else:
            self.render_func = render_func
        if tpl_name and self.render_func is render_template:
            self.render_func = partial(self.render_func, tpl_name)

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
        except Http404Error as e:
            return self.err_func(e, http=404)
        except Http403Error as e:
            return self.err_func(e, http=403)
        # return HTTP500 as final resolution
        except Exception as e:
            return self.err_func(e, http=500)


# for simple rendering of html
class RenderView(View):

    def __init__(self, **kwargs):
        self.d = kwargs

    def dispatch_request(self, **kwargs):
        # we omit the blueprint name
        endp = get_endp()
        # the templates names are
        # doc{,_url,_api,_overview}_html
        return render_template(self.d[endp+'_html'], **kwargs)


# for '/'
class IndexView(RenderView):

    def dispatch_request(self, **kwargs):
        news_file = path_join(current_app.config["local_dir"],
                              self.d['news_html'])
        news = local_info.read_html(news_file)
        return super(IndexView, self).dispatch_request(news=news)


# for /docs/*
class DocView(RenderView):
    """
    Renders page for /doc/*
    """


# for /about/
class AboutView(RenderView):
    """
    Renders page for /about/
    """


# for /prefix/*
class PrefixView(GeneralView):
    """
    TODO
    """


# for /list/*
class ListPackagesView(GeneralView):
    """
    TODO
    """


# NB endp is short for endpoint
class SearchView(GeneralView):

    def get_objects(self, **kwargs):
        if self.render_func == self.recv_search:
            # equality is tested on .im_self, .im_func
            return dict()
        else:
            pass

    # for '/search/'
    def recv_search(self, **kwargs):
        search_form = forms.SearchForm(request.form)
        if search_form.validate_on_submit():
            params = dict(query=search_form.query.data)
            suite = search_form.suite.data
            if suite:
                params["suite"] = suite
            return redirect(url_for(self.d['.search_endp'], **params))
        else:
            # we return the form, to display the errors
            return render_template(self.d['index_html'],
                                   search_form=search_form)

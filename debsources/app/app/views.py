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

from debsources.utils import local_info, path_join

from . import forms


# GENERAL VIEW HANDLING
class GeneralView(View):
    def __init__(self, render_func=render_template, err_func=lambda *x: x):
        """
        render_func: the render function, e.g. jsonify or render_template
        err_func: the function called when an error occurs
        """
        if isinstance(render_func, basestring):
            self.render_func = getattr(self, render_func)
        else:
            self.render_func = render_func

        self.err_func = err_func

    def get_objects(slef, **kwargs):
        return dict()

    def dispatch_request(self, **kwargs):
        """
        renders the view, or call the error function with the error and
        the http error code (404 or 500)
        """
        try:
            context = self.get_objects(**kwargs)
            return self.render_func(**context)
        except Http500Error as e:
            return self.err_func(e, http=500)
        except Http404Error as e:
            return self.err_func(e, http=404)
        except Http403Error as e:
            return self.err_func(e, http=403)


# for '/'
class IndexView(View):

    def __init__(self, **kwargs):
        self.news_html = kwargs['news_html']
        self.index_html = kwargs['index_html']

    def dispatch_request(self, **kwargs):
        news_file = path_join(current_app.config["local_dir"], self.news_html)
        news = local_info.read_html(news_file)

        return render_template(self.index_html, news=news)


# NB endp is short for endpoint
class SearchView(GeneralView):

    def __init__(self, **kwargs):
        self.search_endp = kwargs['search_endp']

        # templates
        self.index_html = kwargs['index_html']

    def get_objects(self, **kwargs):
        # tests on .im_self, .im_func
        if self.render_func == self.recv_search:
            return dict()


    # for '/search/'
    def recv_search(self, **kwargs):
        search_form = forms.SearchForm(request.form)
        if search_form.validate_on_submit():
            params = dict(query=search_form.query.data)
            suite = search_form.suite.data
            if suite:
                params["suite"] = suite
            return redirect(url_for(self.search_endp, **params))
        else:
            # we return the form, to display the errors
            return render_template(self.index_html, search_form=search_form)

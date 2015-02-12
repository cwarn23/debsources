from flask import current_app

# views
from ..app.views import (IndexView, DocView, SearchView, AboutView, PrefixView,
                         ListPackagesView, ChecksumView, CtagView)
# error funcs
from ..app.views import ErrorHandler
from ..app.utils import bind_render
from debsources.app import app_wrapper

from . import bp_sources
from .views import StatsView, SourceView

app = app_wrapper.app

# STATIC FILES
# XXX if the url belongs to a subdomain, then routes registered on app
# won't be triggered.
if app.config.get('serve_static_files'):
    import flask
    @bp_sources.route('/javascript/<path:path>')
    def javascript(path):
        return flask.send_from_directory('/usr/share/javascript/', path)

    @bp_sources.route('/icons/<path:path>')
    def icons(path):
        return flask.send_from_directory('/usr/share/icons/', path)


# INDEXVIEW
bp_sources.add_url_rule(
    '/',
    view_func=IndexView.as_view(
        'index',
        render_func=bind_render('sources/index.html'),
        news_html='sources_news.html'))


# DOCVIEW
bp_sources.add_url_rule(
    '/doc/',
    view_func=DocView.as_view(
        'doc',
        render_func=bind_render('sources/doc.html'),))


bp_sources.add_url_rule(
    '/doc/url/',
    view_func=DocView.as_view(
        'doc_url',
        render_func=bind_render('sources/doc_url.html'),))


bp_sources.add_url_rule(
    '/doc/api/',
    view_func=DocView.as_view(
        'doc_api',
        render_func=bind_render('sources/doc_api.html'),))


bp_sources.add_url_rule(
    '/doc/overview',
    view_func=DocView.as_view(
        'doc_overview',
        render_func=bind_render('sources/doc_overview.html'),))


# ABOUTVIEW
bp_sources.add_url_rule(
    '/about/',
    view_func=AboutView.as_view(
        'about',
        render_func=bind_render('sources/about.html'),))


# STATSVIEW
bp_sources.add_url_rule(
    '/stats/',
    view_func=StatsView.as_view(
        'stats',
        render_func=bind_render('sources/stats.html'),
        err_func=ErrorHandler(bp_name='sources'),
        get_objects='stats',))


bp_sources.add_url_rule(
    '/stats/<suite>/',
    view_func=StatsView.as_view(
        'stats_suite',
        render_func=bind_render('sources/stats_suite.html'),
        err_func=ErrorHandler('sources'),
        get_objects='stats_suite',))


# PREFIXVIEW
bp_sources.add_url_rule(
    '/prefix/<prefix>',
    view_func=PrefixView.as_view(
        'prefix',
        render_func=bind_render('sources/prefix.html'),
        err_func=ErrorHandler('sources'),))


# LISTPACKAGESVIEW
bp_sources.add_url_rule(
    '/list/<int:page>',
    view_func=ListPackagesView.as_view(
        'list_packages',
        render_func=bind_render('sources/list_packages.html'),
        err_func=ErrorHandler('sources'),))


# SEARCHVIEW
bp_sources.add_url_rule(
    '/search/',
    view_func=SearchView.as_view(
        'recv_search',
        render_func=bind_render('sources/index.html'),
        recv_search=True),
    methods=['GET', 'POST'])


bp_sources.add_url_rule(
    '/advanced-search/',
    view_func=SearchView.as_view(
        'advanced_search',
        render_func=bind_render('sources/search_advanced.html'),
        err_func=ErrorHandler('sources'),
        get_objects='advanced',))


bp_sources.add_url_rule(
    '/search/<query>',
    view_func=SearchView.as_view(
        'search',
        render_func=bind_render('sources/search.html'),
        err_func=ErrorHandler('sources'),
        get_objects='query',))


# SOURCEVIEW
bp_sources.add_url_rule(
    '/src/<path:path_to>',
    view_func=SourceView.as_view(
        'source',
        ))
# app.add_url_rule('/src/<path:path_to>/', view_func=SourceView.as_view(
#     'source_html',
#     render_func=lambda **kwargs: render_source_file_html("source_file.html",
#                                                          **kwargs),
#     err_func=lambda e, **kwargs: deal_error(e, mode='html', **kwargs)
# ))


# ChecksumView
bp_sources.add_url_rule(
    '/sha256/',
    view_func=ChecksumView.as_view(
        'checksum',
        render_func=bind_render('sources/checksum.html'),
        err_func=ErrorHandler('sources'),
        pagination=True))


# CtagView
bp_sources.add_url_rule(
    '/ctag/',
    view_func=CtagView.as_view(
        'ctag',
        render_func=bind_render('sources/ctag.html'),
        err_func=ErrorHandler('sources'),
        pagination=True))


# SourceView
# package
# bp_sources.add_url_rule('/src/<package>/', view_func=SourceView.as_view(
#     'source_html',
#     render_func=lambda **kwargs: render_source_file_html("source_file.html",
#                                                          **kwargs),
#     err_func=lambda e, **kwargs: deal_error(e, mode='html', **kwargs)
# ))
bp_sources.add_url_rule(
    '/src/<package>/',
    view_func=SourceView.as_view(
        'source_package',
        err_func=ErrorHandler('sources'),
        get_objects="package"))

# folder and files
bp_sources.add_url_rule(
    '/src/<package>/<path:location>/',
    view_func=SourceView.as_view(
        'source_location',
        err_func=ErrorHandler('sources'),
        get_objects="location"))

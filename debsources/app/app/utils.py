from functools import partial
from math import ceil

from flask import render_template, request, url_for


def bind_render(template, **kwargs):
    return partial(render_template, template, **kwargs)


def format_big_num(num):
    try:
        res = "{:,}".format(num)
    except:
        res = num
    return res


class Pagination(object):

    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def iter_pages(self, left_edge=2, left_current=5,
                   right_current=5, right_edge=2):
        last = 0
        for num in xrange(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and
                num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num

    @staticmethod
    def url_for_other_page(page):
        args = dict(request.args.copy())
        args['page'] = page
        return url_for(request.endpoint, **args)

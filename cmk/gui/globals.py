#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# This is our home-grown version of flask.globals and flask.ctx. It
# can be removed when fully do things the flasky way.

from functools import partial
import logging
from typing import Union  # pylint: disable=unused-import

from werkzeug.local import LocalProxy
from werkzeug.local import LocalStack

import cmk.gui.htmllib  # pylint: disable=unused-import

#####################################################################
# a namespace for storing data during an application context

_sentinel = object()


class _AppCtxGlobals(object):
    def get(self, name, default=None):
        return self.__dict__.get(name, default)

    def pop(self, name, default=_sentinel):
        if default is _sentinel:
            return self.__dict__.pop(name)
        return self.__dict__.pop(name, default)

    def setdefault(self, name, default=None):
        return self.__dict__.setdefault(name, default)

    def __contains__(self, item):
        return item in self.__dict__

    def __iter__(self):
        return iter(self.__dict__)


#####################################################################
# application context

_app_ctx_stack = LocalStack()


def _lookup_app_object(name):
    top = _app_ctx_stack.top
    if top is None:
        raise RuntimeError("Working outside of application context.")
    return getattr(top, name)


class AppContext(object):
    def __init__(self, app):
        self.app = app
        self.g = _AppCtxGlobals()

    def __enter__(self):
        _app_ctx_stack.push(self)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        _app_ctx_stack.pop()


current_app = LocalProxy(partial(_lookup_app_object, "app"))
g = LocalProxy(partial(_lookup_app_object, "g"))

######################################################################
# TODO: This should live somewhere else...


class _PrependURLFilter(logging.Filter):
    def filter(self, record):
        if record.levelno >= logging.ERROR:
            record.msg = "%s %s" % (html.request.requested_url, record.msg)
        return True


######################################################################
# request context

_request_ctx_stack = LocalStack()


def _lookup_req_object(name):
    top = _request_ctx_stack.top
    if top is None:
        raise RuntimeError("Working outside of request context.")
    return getattr(top, name)


class RequestContext(object):
    def __init__(self, html_obj):
        self.html = html_obj

    def __enter__(self):
        _request_ctx_stack.push(self)
        # TODO: Move this plus the corresponding cleanup code to hooks.
        self._web_log_handler = logging.getLogger().handlers[0]
        self._prepend_url_filter = _PrependURLFilter()
        self._web_log_handler.addFilter(self._prepend_url_filter)

        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._web_log_handler.removeFilter(self._prepend_url_filter)
        _request_ctx_stack.pop()
        self.html.finalize()


# NOTE: Flask offers the proxies below, and we should go into that direction,
# too. But currently our html class is a swiss army knife with tons of
# resposibilites which we should really, really split up...
#
# request = LocalProxy(partial(_lookup_req_object, "request"))
# session = LocalProxy(partial(_lookup_req_object, "session"))

html = LocalProxy(partial(_lookup_req_object,
                          "html"))  # type: Union[cmk.gui.htmllib.html, LocalProxy]

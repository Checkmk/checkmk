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

from typing import Any, TYPE_CHECKING  # pylint: disable=unused-import

from werkzeug.local import LocalProxy, LocalStack

#####################################################################
# a namespace for storing data during an application context
# Cyclical import
if TYPE_CHECKING:
    from cmk.gui import htmllib, http  # pylint: disable=unused-import

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
g = LocalProxy(partial(_lookup_app_object, "g"))  # type: Any

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

    if name is None:
        return top

    return getattr(top, name)


class RequestContext(object):
    def __init__(self, html_obj):
        self.html = html_obj
        self.auth_type = None
        # TODO: cyclical import with config -> globals -> config -> ...
        from cmk.gui.config import LoggedInNobody
        self.user = LoggedInNobody()

    # These properties are needed so that we can replace the Request object from within html
    # This actually is a hack which should be removed once the filtering can be done via middleware.
    @property
    def request(self):
        return self.html.request

    @property
    def response(self):
        return self.html.response

    def __enter__(self):
        _request_ctx_stack.push(self)
        # TODO: Move this plus the corresponding cleanup code to hooks.
        self._web_log_handler = logging.getLogger().handlers[0]
        self._prepend_url_filter = _PrependURLFilter()
        self._web_log_handler.addFilter(self._prepend_url_filter)

        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._web_log_handler.removeFilter(self._prepend_url_filter)
        # TODO: html.finalize needs to be called before popping the stack, because it does
        #       something with the user object.
        self.html.finalize()
        _request_ctx_stack.pop()


# NOTE: Flask offers the proxies below, and we should go into that direction,
# too. But currently our html class is a swiss army knife with tons of
# responsibilities which we should really, really split up...
def request_local_attr(name=None):
    """Delegate access to the corresponding attribute on RequestContext

    When the returned object is accessed, the Proxy will fetch the current
    RequestContext from the LocalStack and return the attribute given by `name`.

    Args:
        name (str): The name of the attribute on RequestContext

    Returns:
        A proxy which wraps the value stored on RequestContext.

    """
    return LocalProxy(partial(_lookup_req_object, name))


local = request_local_attr()  # None as name will get the whole object.

user = request_local_attr('user')
request = request_local_attr('request')
response = request_local_attr('response')
html = request_local_attr('html')

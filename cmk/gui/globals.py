#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This is our home-grown version of flask.globals and flask.ctx. It
# can be removed when fully do things the flasky way.

from functools import partial
import logging

from typing import TYPE_CHECKING

from werkzeug.local import LocalProxy, LocalStack

#####################################################################
# a namespace for storing data during an application context
# Cyclical import

if TYPE_CHECKING:
    from typing import Any  # pylint: disable=unused-import
    from cmk.gui import htmllib, http, config  # pylint: disable=unused-import

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
            record.msg = "%s %s" % (request.requested_url, record.msg)
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
    def __init__(self, html_obj=None, req=None, resp=None):
        self.html = html_obj
        self.auth_type = None

        if req is None and html_obj:
            req = html_obj.request
        if resp is None and html_obj:
            resp = html_obj.response

        self.request = req
        self.response = resp
        # TODO: cyclical import with config -> globals -> config -> ...
        from cmk.gui.config import LoggedInNobody
        self.user = LoggedInNobody()

    def __enter__(self):
        _request_ctx_stack.push(self)
        # TODO: Move this plus the corresponding cleanup code to hooks.
        self._web_log_handler = logging.getLogger().handlers[0]
        self._prepend_url_filter = _PrependURLFilter()
        self._web_log_handler.addFilter(self._prepend_url_filter)

        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._web_log_handler.removeFilter(self._prepend_url_filter)
        # html.finalize needs to be called before popping the stack, because it does
        # something with the user object. We make this optional, so we can use the RequestContext
        # without the html object (for APIs for example).
        if self.html is not None:
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

# NOTE: All types FOO below are actually a Union[Foo, LocalProxy], but
# LocalProxy is meant as a transparent proxy, so we leave it out to de-confuse
# mypy. LocalProxy uses a lot of reflection magic, which can't be understood by
# tools in general.
user = request_local_attr('user')  # type: config.LoggedInUser
request = request_local_attr('request')  # type: http.Request

html = request_local_attr('html')  # type: htmllib.html

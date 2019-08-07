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

# Imports are needed for type hints. These type hints are useful for
# editors completion of "html" object methods and for mypy.
from functools import partial
from typing import Union  # pylint: disable=unused-import

from werkzeug.local import LocalProxy
from werkzeug.local import LocalStack

import cmk.gui.htmllib  # pylint: disable=unused-import

######################################################################
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
        self.g = {}

    def __enter__(self):
        _app_ctx_stack.push(self)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        _app_ctx_stack.pop()


current_app = LocalProxy(partial(_lookup_app_object, "app"))
g = LocalProxy(partial(_lookup_app_object, "g"))

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
        return self

    def __exit__(self, exc_type, exc_value, tb):
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

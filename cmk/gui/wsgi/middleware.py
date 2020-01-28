#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
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
import functools
import wsgiref.util

from cmk.gui import http
from cmk.gui.globals import AppContext, RequestContext


def with_context_middleware(app):
    """Middleware which constructs the right context on each request.

    """
    @functools.wraps(app)
    def with_context(environ, start_response):
        req = http.Request(environ)
        resp = http.Response(is_secure=req.is_secure)
        with AppContext(app), RequestContext(req=req, resp=resp):
            return app(environ, start_response)

    return with_context


def apache_env(app):
    """Add missing WSGI environment keys when a request comes from Apache."""
    @functools.wraps(app)
    def _add_apache_env(environ, start_response):
        if not environ.get('REQUEST_URI'):
            environ['REQUEST_URI'] = wsgiref.util.request_uri(environ)

        path_info = environ.get('PATH_INFO')
        if not path_info or path_info == '/':
            environ['PATH_INFO'] = environ['SCRIPT_NAME']

        return app(environ, start_response)

    return _add_apache_env


class OverrideRequestMethod(object):
    """Middleware to allow inflexible clients to override the HTTP request method.

    Common convention is to allow for an X-HTTP-Method-Override HTTP header to be set.

    Please be aware no validation for a "correct" HTTP verb will be done by this middleware,
    as this should be handled by other layers.
    """
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ, start_response):
        override = environ.get('HTTP_X_HTTP_METHOD_OVERRIDE')
        if override:
            environ['REQUEST_METHOD'] = override
        return self.app(environ, start_response)

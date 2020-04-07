#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
        with AppContext(app), RequestContext(req=req):
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
            if environ['REQUEST_METHOD'].lower() == 'post':
                environ['REQUEST_METHOD'] = override
        return self.app(environ, start_response)

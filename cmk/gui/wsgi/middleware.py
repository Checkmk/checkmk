#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools

from cmk.gui import hooks


class CallHooks:
    def __init__(self, app) -> None:
        self.app = app

    def __call__(self, environ, start_response):
        hooks.call("request-start")
        response = self.app(environ, start_response)
        hooks.call("request-end")
        return response


def recreate_apache_env(app):
    """Recreate the environment as if it comes from Apache."""

    @functools.wraps(app)
    def _add_apache_env(environ, start_response):
        # mod_proxy will result in a broken request_uri. To recreate this environment in the
        # unit tests, we need to add SCRIPT_NAME.
        if environ.get("paste.testing"):
            # We only want to do this in testing. webtest.TestApp will set this key.
            environ["SCRIPT_NAME"] = environ.get("PATH_INFO")

        return app(environ, start_response)

    return _add_apache_env


def fix_apache_env(app):
    """Remove superfluous environment keys when a request comes from Apache."""

    @functools.wraps(app)
    def _fix_apache_env(environ, start_response):
        environ["SCRIPT_NAME"] = ""

        return app(environ, start_response)

    return _fix_apache_env


class OverrideRequestMethod:
    """Middleware to allow inflexible clients to override the HTTP request method.

    Common convention is to allow for an X-HTTP-Method-Override HTTP header to be set.

    Please be aware no validation for a "correct" HTTP verb will be done by this middleware,
    as this should be handled by other layers.
    """

    def __init__(self, app) -> None:
        self.app = app

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ, start_response):
        override = environ.get("HTTP_X_HTTP_METHOD_OVERRIDE")
        if override:
            if environ["REQUEST_METHOD"].lower() == "post":
                environ["REQUEST_METHOD"] = override
        return self.app(environ, start_response)

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import abc
from typing import final
from wsgiref.types import StartResponse, WSGIApplication, WSGIEnvironment

from cmk.gui.wsgi.type_defs import WSGIResponse


class AbstractWSGIMiddleware(abc.ABC):
    @final
    def __init__(self, app: WSGIApplication) -> None:
        self.app = app

    @final
    def __call__(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        return self.wsgi_app(environ, start_response)

    @abc.abstractmethod
    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        raise NotImplementedError


class OverrideRequestMethod(AbstractWSGIMiddleware):
    """Middleware to allow inflexible clients to override the HTTP request method.

    Common convention is to allow for an X-HTTP-Method-Override HTTP header to be set.

    Please be aware no validation for a "correct" HTTP verb will be done by this middleware,
    as this should be handled by other layers.
    """

    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        override = environ.get("HTTP_X_HTTP_METHOD_OVERRIDE")
        if override:
            if environ["REQUEST_METHOD"].lower() == "post":
                environ["REQUEST_METHOD"] = override
        return self.app(environ, start_response)


class AuthenticationMiddleware(AbstractWSGIMiddleware):
    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        return self.app(environ, start_response)

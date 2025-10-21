#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper functions for executing GUI code in external scripts.

The intended use is for scripts such as cmk-update-config or init-redis.
"""

import typing
from collections.abc import Iterator
from contextlib import contextmanager
from functools import cache
from wsgiref.types import WSGIEnvironment

from flask import Flask
from flask.ctx import RequestContext
from werkzeug.test import create_environ

from cmk.ccc.version import edition
from cmk.gui.http import Response
from cmk.utils import paths

Environments = typing.Literal["production", "testing", "development"]


@cache
def session_wsgi_app(debug: bool = False, testing: bool = False) -> Flask:
    # TODO: Temporary hack. Can be removed once #12954 has been ported from 2.0.0
    from cmk.gui.wsgi.app import make_wsgi_app

    # For now always use the detected edition. At some point make this parameterized
    return make_wsgi_app(edition(paths.omd_root), debug=debug, testing=testing)


def _make_request_context(app: Flask, environ: WSGIEnvironment | None = None) -> RequestContext:
    if environ is None:
        environ = create_environ()
    return app.request_context(environ)


@contextmanager
def request_context(app: Flask, environ: WSGIEnvironment | None = None) -> Iterator[None]:
    with _make_request_context(app, environ):
        app.preprocess_request()
        yield
        app.process_response(Response())


@contextmanager
def application_and_request_context(environ: WSGIEnvironment | None = None) -> Iterator[None]:
    app = session_wsgi_app(testing=True)
    with app.app_context(), request_context(app, environ):
        yield


@contextmanager
def gui_context(environ: WSGIEnvironment | None = None) -> Iterator[None]:
    app = session_wsgi_app(testing=True)
    with app.app_context(), _make_request_context(app, environ):
        yield

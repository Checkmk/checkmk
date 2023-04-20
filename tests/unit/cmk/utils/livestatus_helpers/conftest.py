#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from flask import Flask
from flask.ctx import RequestContext
from werkzeug.test import create_environ

from cmk.gui.utils.script_helpers import session_wsgi_app


@contextmanager
def application_context(app: Flask) -> Iterator[None]:
    with app.app_context():
        yield


def make_request_context(app: Flask, environ: dict[str, Any] | None = None) -> RequestContext:
    if environ is None:
        environ = create_environ()
    return app.request_context(environ)


@contextmanager
def request_context(app: Flask, environ: dict[str, Any] | None = None) -> Iterator[None]:
    with make_request_context(app, environ):
        from cmk.gui.wsgi.blueprints.global_vars import set_global_vars

        set_global_vars()
        yield


@contextmanager
def application_and_request_context(environ: dict[str, Any] | None = None) -> Iterator[None]:
    app = session_wsgi_app(testing=True)
    with application_context(app), request_context(app, environ):
        yield


@contextmanager
def gui_context(environ: dict[str, Any] | None = None) -> Iterator[None]:
    app = session_wsgi_app(testing=True)
    with application_context(app), request_context(app, environ):
        yield


@pytest.fixture
def with_request_context() -> Iterator[None]:
    environ = create_environ()
    with application_and_request_context(environ):
        yield

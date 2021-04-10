#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper functions for executing GUI code in external scripts.

The intended use is for scripts such as cmk-update-config or init-redis.
"""

from contextlib import contextmanager
from typing import (
    Any,
    Iterator,
    Mapping,
)

from werkzeug.test import create_environ

from cmk.gui.config import (
    load_config,
    set_super_user,
)
from cmk.gui.display_options import DisplayOptions
from cmk.gui.globals import (
    AppContext,
    RequestContext,
)
from cmk.gui.htmllib import html
from cmk.gui.http import Request
from cmk.gui.modules import load_all_plugins


# TODO: Better make our application available?
class DummyApplication:
    def __init__(self, environ, start_response):
        self._environ = environ
        self._start_response = start_response


@contextmanager
def application_context(environ: Mapping[str, Any]) -> Iterator[None]:
    with AppContext(DummyApplication(environ, None)):
        yield


@contextmanager
def request_context(environ: Mapping[str, Any]) -> Iterator[None]:
    this_html = html(Request(environ))

    # Currently the htmllib.html constructor enables the timeout by default. This side effect
    # should really be cleaned up.
    this_html.disable_request_timeout()

    with RequestContext(
            this_html,
            display_options=DisplayOptions(),
            prefix_logs_with_url=False,
    ):
        yield


@contextmanager
def application_and_request_context() -> Iterator[None]:
    environ = dict(create_environ(), REQUEST_URI='')
    with application_context(environ), request_context(environ):
        yield


def initialize_gui_environment() -> None:
    load_all_plugins()
    load_config()
    set_super_user()

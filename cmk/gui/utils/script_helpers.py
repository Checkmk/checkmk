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
    Optional,
)

from werkzeug.test import create_environ

from cmk.gui.config import load_config, make_config_object, get_default_config
from cmk.gui.display_options import DisplayOptions
from cmk.gui.utils.theme import Theme
from cmk.gui.globals import (
    AppContext,
    RequestContext,
)
from cmk.gui.htmllib import html
from cmk.gui.http import Request, Response
from cmk.gui.utils.output_funnel import OutputFunnel
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
    req = Request(environ)
    resp = Response(mimetype="text/html")
    funnel = OutputFunnel(resp)
    with RequestContext(
            req=req,
            resp=resp,
            funnel=funnel,
            config_obj=make_config_object(get_default_config()),
            html_obj=html(req, resp, funnel, output_format="html"),
            display_options=DisplayOptions(),
            theme=Theme(),
            prefix_logs_with_url=False,
    ):
        yield


@contextmanager
def application_and_request_context(environ: Optional[Mapping[str, Any]] = None) -> Iterator[None]:
    if environ is None:
        environ = dict(create_environ(), REQUEST_URI='')
    with application_context(environ), request_context(environ):
        yield


def initialize_gui_environment() -> None:
    load_config()
    load_all_plugins()

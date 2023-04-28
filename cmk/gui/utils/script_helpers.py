#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper functions for executing GUI code in external scripts.

The intended use is for scripts such as cmk-update-config or init-redis.
"""

from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Iterator, Mapping, Optional

from werkzeug.test import create_environ

from cmk.gui.config import get_default_config, load_config, make_config_object
from cmk.gui.display_options import DisplayOptions
from cmk.gui.globals import AppContext, RequestContext
from cmk.gui.htmllib import html
from cmk.gui.http import Request, Response
from cmk.gui.utils.logged_in import LoggedInNobody
from cmk.gui.utils.output_funnel import OutputFunnel
from cmk.gui.utils.theme import Theme
from cmk.gui.utils.timeout_manager import TimeoutManager


@lru_cache
def session_wsgi_app(debug):
    # TODO: Temporary hack. Can be removed once #12954 has been ported from 2.0.0
    from cmk.gui.wsgi import make_app

    return make_app(debug=debug)


@contextmanager
def application_context() -> Iterator[None]:
    with AppContext(session_wsgi_app(debug=False)):
        yield


def make_request_context(environ: Optional[Mapping[str, Any]] = None) -> RequestContext:
    req = Request(dict(create_environ(), REQUEST_URI="") if environ is None else environ)
    resp = Response(mimetype="text/html")
    funnel = OutputFunnel(resp)
    return RequestContext(
        req=req,
        resp=resp,
        funnel=funnel,
        config_obj=make_config_object(get_default_config()),
        user=LoggedInNobody(),
        html_obj=html(req, resp, funnel, output_format="html"),
        display_options=DisplayOptions(),
        timeout_manager=TimeoutManager(),
        theme=Theme(),
        prefix_logs_with_url=False,
    )


@contextmanager
def request_context(environ: Optional[Mapping[str, Any]] = None) -> Iterator[None]:
    with make_request_context(environ=environ):
        yield


@contextmanager
def application_and_request_context(environ: Optional[Mapping[str, Any]] = None) -> Iterator[None]:
    with application_context(), request_context(environ):
        yield


@contextmanager
def gui_context(environ: Optional[Mapping[str, Any]] = None) -> Iterator[None]:
    with application_context(), request_context(environ):
        load_config()
        yield

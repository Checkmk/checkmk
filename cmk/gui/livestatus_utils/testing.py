#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import os
from typing import ContextManager, Generator
from unittest import mock

from werkzeug.test import EnvironBuilder

from livestatus import MultiSiteConnection

from cmk.utils.livestatus_helpers.testing import MatchType, MockLiveStatusConnection
from cmk.utils.site import omd_site

from cmk.gui import http, sites
from cmk.gui.config import get_default_config, make_config_object
from cmk.gui.context import AppContext, RequestContext
from cmk.gui.ctx_stack import app_stack, request_stack
from cmk.gui.display_options import DisplayOptions
from cmk.gui.globals import PrependURLFilter
from cmk.gui.htmllib import html
from cmk.gui.utils.logged_in import LoggedInNobody
from cmk.gui.utils.output_funnel import OutputFunnel


@contextlib.contextmanager
def mock_livestatus(
    with_context: bool = False, with_html: bool = False
) -> Generator[MockLiveStatusConnection, None, None]:
    live = MockLiveStatusConnection()

    env = EnvironBuilder().get_environ()
    req = http.Request(env)
    resp = http.Response()

    app_context: ContextManager
    req_context: ContextManager
    if with_html:
        html_obj = None
    else:
        html_obj = html(
            request=req,
            response=resp,
            output_funnel=OutputFunnel(resp),
            output_format="html",
        )
    if with_context:
        app_context = AppContext(None, stack=app_stack())
        req_context = RequestContext(
            html_obj=html_obj,
            req=req,
            resp=resp,
            funnel=OutputFunnel(resp),
            config_obj=make_config_object(get_default_config()),
            user=LoggedInNobody(),
            display_options=DisplayOptions(),
            prefix_logs_with_url=False,
            stack=request_stack(),
            url_filter=PrependURLFilter(),
        )
    else:
        app_context = contextlib.nullcontext()
        req_context = contextlib.nullcontext()

    with app_context, req_context, mock.patch(
        "cmk.gui.sites._get_enabled_and_disabled_sites", new=live.enabled_and_disabled_sites
    ), mock.patch(
        "livestatus.MultiSiteConnection.expect_query", new=live.expect_query, create=True
    ), mock.patch(
        "livestatus.SingleSiteConnection._create_socket", new=live.create_socket
    ), mock.patch.dict(
        os.environ, {"OMD_ROOT": "/", "OMD_SITE": "NO_SITE"}
    ):

        # We don't want to be polluted by other tests.
        omd_site.cache_clear()
        yield live
        # We don't want to pollute other tests.
        omd_site.cache_clear()


@contextlib.contextmanager
def simple_expect(
    query="",
    match_type: MatchType = "loose",
    expect_status_query: bool = True,
) -> Generator[MultiSiteConnection, None, None]:
    """A simplified testing context manager.

    Args:
        query:
            A livestatus query.

        match_type:
            Either 'strict', 'loose' or 'ellipsis'. Default is 'loose'.

        expect_status_query:
            If the query of the status table (which Checkmk does when calling sites.live()) should
            be expected. Defaults to False.

    Returns:
        A context manager.

    Examples:

        >>> with simple_expect("GET hosts") as _live:
        ...    _ = _live.query("GET hosts")

    """
    with mock_livestatus(with_context=True) as mock_live:
        if query:
            mock_live.expect_query(query, match_type=match_type)
        with mock_live(expect_status_query=expect_status_query):
            yield sites.live()

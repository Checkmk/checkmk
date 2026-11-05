#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.pages import PageContext
from cmk.gui.session import session
from cmk.gui.wato.pages.hosts import PageAjaxAgentReceiverPort, PageAjaxDiagCmkAgent


def _page_context() -> PageContext:
    request.set_var("_csrf_token", str(session.session_info.csrf_token))
    return PageContext(config=Config(), request=request)


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_agent_diagnose_via_an_unknown_site_reports_an_error() -> None:
    request.set_var("request", json.dumps({"site_id": "gone", "host_name": "heute"}))

    result = PageAjaxDiagCmkAgent().page(_page_context())

    assert isinstance(result, dict)
    assert result["status_code"] == 99
    assert "gone" in result["output"]


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_agent_receiver_port_of_an_unknown_site_is_the_default() -> None:
    request.set_var("site_id", "gone")

    result = PageAjaxAgentReceiverPort().page(_page_context())

    assert isinstance(result, dict)
    assert result["is_default"] is True

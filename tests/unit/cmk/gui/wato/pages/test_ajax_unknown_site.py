#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.pages import AjaxPage, PageContext
from cmk.gui.permissions import all_permissions
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.wato.pages.hosts import (
    PageAjaxAgentReceiverPort,
    PageAjaxDiagCmkAgent,
    PageAjaxDiagSnmp,
)


def _page_context() -> PageContext:
    config = Config()
    return PageContext(
        config=config,
        request=request,
        transactions=transactions,
        session=session,
        user_permissions=UserPermissions.from_config(config, all_permissions()),
    )


@pytest.mark.parametrize(
    "page",
    [
        pytest.param(PageAjaxDiagCmkAgent(), id="agent"),
        pytest.param(PageAjaxDiagSnmp(), id="snmp"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_diagnose_via_an_unknown_site_reports_an_error(page: AjaxPage) -> None:
    request.set_var("request", json.dumps({"site_id": "gone", "host_name": "heute"}))

    result = page.page(_page_context())

    assert isinstance(result, dict)
    assert result["status_code"] == 99
    assert "gone" in result["output"]


@pytest.mark.usefixtures("request_context")
def test_agent_receiver_port_of_an_unknown_site_is_the_default() -> None:
    request.set_var("site_id", "gone")

    result = PageAjaxAgentReceiverPort().page(_page_context())

    assert isinstance(result, dict)
    assert result["is_default"] is True

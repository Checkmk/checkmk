#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.config import Config
from cmk.gui.http import Request, request
from cmk.gui.pages import PageContext
from cmk.gui.permissions import all_permissions
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.views.page_ajax_reschedule import PageRescheduleCheck
from cmk.livestatus_client.testing import MockLiveStatusConnection


class _RequestReturning:
    def __init__(self, api_request: dict[str, object]) -> None:
        self._api_request = api_request
        self.remote_ip = "127.0.0.1"

    def get_request(self, *_args: object, **_kwargs: object) -> dict[str, object]:
        return self._api_request

    def get_str_input(self, *_args: object, **_kwargs: object) -> None:
        return None


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_reschedule_rejects_a_host_not_visible_to_the_user(
    load_config: Config, mock_livestatus: MockLiveStatusConnection
) -> None:
    page_request = _RequestReturning(
        {
            "site": "NO_SITE",
            "host": "host-secret",
            "_csrf_token": session.session_info.csrf_token,
        }
    )
    ctx = PageContext(
        config=load_config,
        request=cast(Request, page_request),
        transactions=transactions,
        session=session,
        user_permissions=UserPermissions.from_config(load_config, all_permissions()),
    )
    mock_livestatus.expect_query(
        "GET hosts\nColumns: host_name\nFilter: host_name = host-secret", sites=["NO_SITE"]
    )

    with mock_livestatus, pytest.raises(MKGeneralException, match="not found"):
        PageRescheduleCheck().page(ctx)


def _page_context(config: Config, **request_vars: str) -> PageContext:
    for name, value in request_vars.items():
        request.set_var(name, value)
    request.set_var("_csrf_token", session.session_info.csrf_token)
    return PageContext(
        config=config,
        request=request,
        transactions=transactions,
        session=session,
        user_permissions=UserPermissions.from_config(config, all_permissions()),
    )


def _add_services(mock_livestatus: MockLiveStatusConnection, *names: str) -> None:
    mock_livestatus.add_table(
        "services",
        [
            {
                "host_name": "heute",
                "description": name,
                "service_description": name,
                "last_check": 0,
                "state": 0,
                "plugin_output": "OK",
            }
            for name in names
        ],
        site="NO_SITE",
    )


def _wait_query(service: str, wait_timeout: str) -> str:
    return (
        f"GET services\nWaitObject: heute;{service}\nWaitCondition: last_check >= ...\n"
        f"WaitTimeout: {wait_timeout}\nWaitTrigger: check\n"
        "Columns: last_check state plugin_output\nFilter: host_name = heute\n"
        f"Filter: service_description = {service}\nColumnHeaders: off"
    )


def _expect_visibility_check(mock_livestatus: MockLiveStatusConnection, service: str) -> None:
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name\nFilter: host_name = heute\n"
        f"Filter: service_description = {service}",
        sites=["NO_SITE"],
    )


def _expect_check_mk_then_discovery(
    mock_livestatus: MockLiveStatusConnection, discovery: str
) -> None:
    _add_services(mock_livestatus, "Check_MK", discovery)
    _expect_visibility_check(mock_livestatus, discovery)
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_FORCED_SVC_CHECK;heute;Check_MK;...", match_type="ellipsis"
    )
    mock_livestatus.expect_query(
        _wait_query("Check_MK", "..."), match_type="ellipsis", sites=["NO_SITE"]
    )
    mock_livestatus.expect_query(
        f"COMMAND [...] SCHEDULE_FORCED_SVC_CHECK;heute;{discovery};...",
        match_type="ellipsis",
    )


@pytest.mark.parametrize(
    "discovery",
    [
        pytest.param("Check_MK Discovery", id="current-name"),
        pytest.param("Check_MK inventory", id="old-name"),
    ],
)
@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_rescheduling_discovery_reschedules_check_mk_first(
    load_config: Config, mock_livestatus: MockLiveStatusConnection, discovery: str
) -> None:
    ctx = _page_context(load_config, site="NO_SITE", host="heute", service=discovery)
    _expect_check_mk_then_discovery(mock_livestatus, discovery)
    mock_livestatus.expect_query(
        _wait_query(discovery, "..."), match_type="ellipsis", sites=["NO_SITE"]
    )

    with mock_livestatus:
        PageRescheduleCheck().page(ctx)

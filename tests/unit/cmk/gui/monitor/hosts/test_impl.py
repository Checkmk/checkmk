#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.gui import sites
from cmk.gui.monitor.hosts._impl import _wato_folder_from_filename, LiveStatusHostRepository
from cmk.gui.monitor.hosts._models import HostState
from cmk.gui.session import SuperUserContext
from cmk.livestatus_client.testing import MockLiveStatusConnection


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("/wato/hosts.mk", "/"),
        ("/wato/network/switches/hosts.mk", "/network/switches"),
        ("/wato/network/hosts.mk", "/network"),
        ("/omd/sites/heute/etc/nagios/conf.d/hosts.mk", None),
        ("/wato/network/switches/other.mk", None),
    ],
)
def test_wato_folder_from_filename(filename: str, expected: str | None) -> None:
    assert _wato_folder_from_filename(filename) == expected


def _host_row(*, has_been_checked: int, state: int) -> dict[str, object]:
    return {
        "name": "myhost",
        "alias": "myhost",
        "address": "127.0.0.1",
        "state": state,
        "has_been_checked": has_been_checked,
        "num_services": 3,
        "num_services_ok": 3,
        "num_services_warn": 0,
        "num_services_crit": 0,
        "num_services_unknown": 0,
        "num_services_pending": 0,
        "acknowledged": 0,
        "scheduled_downtime_depth": 0,
        "last_check": 1700000000,
        "last_state_change": 1699999000,
        "contact_groups": ["all"],
        "tags": {"criticality": "prod"},
        "labels": {"cmk/os_family": "linux"},
        "label_sources": {"cmk/os_family": "discovered"},
        "custom_variables": {"CUSTOMER": "acme"},
        "filename": "/wato/hosts.mk",
    }


@pytest.mark.usefixtures("request_context")
def test_get_overview_never_checked_host_is_pending(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    # Regression test for a crash (KeyError: 'has_been_checked') that happened because
    # ``get_overview``'s query didn't request that column, even though it reads it to
    # detect a host that has never been checked.
    mock_livestatus.add_table("hosts", [_host_row(has_been_checked=0, state=0)])
    with mock_livestatus(expect_status_query=True), SuperUserContext():
        mock_livestatus.expect_query(
            ["GET hosts", "Filter: name = myhost"], match_type="loose", sites=["NO_SITE"]
        )
        repo = LiveStatusHostRepository(connection=sites.live())
        overview = repo.get_overview(hostname="myhost", site_id="NO_SITE")

    assert overview.state is HostState.PENDING


@pytest.mark.usefixtures("request_context")
def test_get_overview_checked_host_uses_reported_state(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table("hosts", [_host_row(has_been_checked=1, state=1)])
    with mock_livestatus(expect_status_query=True), SuperUserContext():
        mock_livestatus.expect_query(
            ["GET hosts", "Filter: name = myhost"], match_type="loose", sites=["NO_SITE"]
        )
        repo = LiveStatusHostRepository(connection=sites.live())
        overview = repo.get_overview(hostname="myhost", site_id="NO_SITE")

    assert overview.state is HostState.DOWN

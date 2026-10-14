#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
import json
import time
from collections.abc import Sequence
from http import HTTPStatus

import pytest

from cmk.gui.monitor.hosts._api._reschedule import _handle_reschedule_checks, RescheduleHostRef
from cmk.gui.monitor.hosts._impl import LiveStatusHostActions
from cmk.gui.monitor.hosts._models import HostTarget
from cmk.livestatus_client import MultiSiteConnection
from cmk.livestatus_client.testing import mock_site_configurations, MockLiveStatusConnection
from tests.unit.cmk.web_test_app import WebTestAppForCMK

# datetime has microsecond resolution, so the round-trip through
# datetime.fromtimestamp can shave a sub-microsecond fraction off the captured
# time. Allow that when asserting a check time is not scheduled in the past.
_DATETIME_RESOLUTION_S = 1e-6


class _FakeHostRescheduler:
    def __init__(self) -> None:
        self.targets: list[HostTarget] = []
        self.start: dt.datetime | None = None
        self.spread: dt.timedelta | None = None

    def reschedule(
        self, targets: Sequence[HostTarget], *, start: dt.datetime, spread: dt.timedelta
    ) -> int:
        self.targets = list(targets)
        self.start = start
        self.spread = spread
        return len(targets)


def _host(site_id: str, name: str) -> RescheduleHostRef:
    return RescheduleHostRef(site_id=site_id, name=name)


def test_handle_reschedule_checks_empty_hosts_does_not_touch_rescheduler() -> None:
    rescheduler = _FakeHostRescheduler()

    response = _handle_reschedule_checks(rescheduler, hosts=[], spread_minutes=5)

    assert response.rescheduled == 0
    assert rescheduler.targets == []


def test_handle_reschedule_checks_reschedules_every_host() -> None:
    rescheduler = _FakeHostRescheduler()
    hosts = [_host("local", "web-01"), _host("remote", "web-02")]

    response = _handle_reschedule_checks(rescheduler, hosts=hosts, spread_minutes=0)

    assert response.rescheduled == 2
    assert [(t.site_id, t.host_name) for t in rescheduler.targets] == [
        ("local", "web-01"),
        ("remote", "web-02"),
    ]


def test_handle_reschedule_checks_without_spread_schedules_immediately() -> None:
    rescheduler = _FakeHostRescheduler()
    hosts = [_host("local", "web-01"), _host("local", "web-02")]

    before = time.time()
    _handle_reschedule_checks(rescheduler, hosts=hosts, spread_minutes=0)
    after = time.time()

    assert rescheduler.start is not None
    assert before - _DATETIME_RESOLUTION_S <= rescheduler.start.timestamp() <= after
    assert rescheduler.spread == dt.timedelta(0)


def test_handle_reschedule_checks_passes_on_the_requested_spread() -> None:
    rescheduler = _FakeHostRescheduler()
    hosts = [_host("local", f"web-{index:02}") for index in range(4)]

    _handle_reschedule_checks(rescheduler, hosts=hosts, spread_minutes=10)

    assert rescheduler.spread == dt.timedelta(minutes=10)


@pytest.mark.usefixtures("with_admin_login")
def test_reschedule_checks_refuses_hosts_not_visible_to_the_user(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query(
        "GET hosts\nColumns: name\nFilter: name = host-secret", sites=["NO_SITE"]
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/hosts/actions/reschedule",
            params=json.dumps({"hosts": [{"site_id": "NO_SITE", "name": "host-secret"}]}),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            status=HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    assert resp.json["title"] == "None of the hosts was found"


def test_reschedule_spreads_the_checks_over_the_visible_hosts_only(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    start = dt.datetime.fromtimestamp(1767225600)
    mock_livestatus.add_table("hosts", [{"name": "web-01"}, {"name": "web-03"}], site="local")
    mock_livestatus.expect_query(
        "GET hosts\nColumns: name\nFilter: name = web-01\nFilter: name = web-02\n"
        "Filter: name = web-03\nOr: 3",
        sites=["local"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_FORCED_HOST_CHECK;web-01;1767225600",
        match_type="ellipsis",
        sites=["local"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_FORCED_HOST_CHECK;web-03;1767225900",
        match_type="ellipsis",
        sites=["local"],
    )

    with mock_livestatus(expect_status_query=False):
        rescheduled = LiveStatusHostActions(
            connection=MultiSiteConnection(sites=mock_site_configurations(mock_livestatus.sites))
        ).reschedule(
            [
                HostTarget("local", "web-01"),
                HostTarget("local", "web-02"),
                HostTarget("local", "web-03"),
            ],
            start=start,
            spread=dt.timedelta(minutes=10),
        )

    assert rescheduled == 2

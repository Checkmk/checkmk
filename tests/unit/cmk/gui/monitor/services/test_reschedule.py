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

import cmk.utils.paths
from cmk.gui.monitor.services._api._reschedule import (
    _handle_reschedule_checks,
    RescheduleServiceRef,
)
from cmk.gui.monitor.services._impl import LiveStatusServiceActions
from cmk.gui.monitor.services._models import ServiceTarget
from cmk.livestatus_client import MultiSiteConnection
from cmk.livestatus_client.testing import mock_site_configurations, MockLiveStatusConnection
from tests.testlib.unit.gui.setup_git_test_helper import (
    init_setup_git_repo,
    setup_git_commit_subjects,
)
from tests.testlib.unit.gui.web_test_app import SetConfig, WebTestAppForCMK

# datetime has microsecond resolution, so the round-trip through
# datetime.fromtimestamp can shave a sub-microsecond fraction off the captured
# time. Allow that when asserting a check time is not scheduled in the past.
_DATETIME_RESOLUTION_S = 1e-6


class _FakeServiceRescheduler:
    def __init__(self) -> None:
        self.targets: list[ServiceTarget] = []
        self.start: dt.datetime | None = None
        self.spread: dt.timedelta | None = None

    def reschedule(
        self, targets: Sequence[ServiceTarget], *, start: dt.datetime, spread: dt.timedelta
    ) -> int:
        self.targets = list(targets)
        self.start = start
        self.spread = spread
        return len(targets)


def _service(site_id: str, host_name: str, name: str) -> RescheduleServiceRef:
    return RescheduleServiceRef(site_id=site_id, host_name=host_name, name=name)


def test_handle_reschedule_checks_empty_services_does_not_touch_rescheduler() -> None:
    rescheduler = _FakeServiceRescheduler()

    response = _handle_reschedule_checks(
        rescheduler, services=[], spread_minutes=5, wait_timeout=10.0
    )

    assert response.rescheduled == 0
    assert rescheduler.targets == []


def test_handle_reschedule_checks_reschedules_every_service() -> None:
    rescheduler = _FakeServiceRescheduler()
    services = [
        _service("local", "web-01", "CPU load"),
        _service("remote", "web-02", "Memory"),
    ]

    response = _handle_reschedule_checks(
        rescheduler, services=services, spread_minutes=0, wait_timeout=10.0
    )

    assert response.rescheduled == 2
    assert [(t.site_id, t.host_name, t.description) for t in rescheduler.targets] == [
        ("local", "web-01", "CPU load"),
        ("remote", "web-02", "Memory"),
    ]


def test_handle_reschedule_checks_without_spread_schedules_immediately() -> None:
    rescheduler = _FakeServiceRescheduler()
    services = [
        _service("local", "web-01", "CPU load"),
        _service("local", "web-01", "Memory"),
    ]

    before = time.time()
    _handle_reschedule_checks(rescheduler, services=services, spread_minutes=0, wait_timeout=10.0)
    after = time.time()

    assert rescheduler.start is not None
    assert before - _DATETIME_RESOLUTION_S <= rescheduler.start.timestamp() <= after
    assert rescheduler.spread == dt.timedelta(0)


def test_handle_reschedule_checks_passes_on_the_requested_spread() -> None:
    rescheduler = _FakeServiceRescheduler()
    services = [_service("local", "web-01", f"Filesystem /mnt/{index}") for index in range(4)]

    _handle_reschedule_checks(rescheduler, services=services, spread_minutes=10, wait_timeout=10.0)

    assert rescheduler.spread == dt.timedelta(minutes=10)


def test_handle_reschedule_checks_tells_since_when_to_wait_for_the_check() -> None:
    before = int(time.time())

    response = _handle_reschedule_checks(
        _FakeServiceRescheduler(),
        services=[_service("local", "web-01", "CPU load")],
        spread_minutes=0,
        wait_timeout=10.0,
    )

    assert before <= response.scheduled_at <= int(time.time())


@pytest.mark.usefixtures("with_admin_login")
def test_reschedule_checks_does_not_commit_the_setup_git_repo(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    set_config: SetConfig,
) -> None:
    config_dir = cmk.utils.paths.default_config_dir
    init_setup_git_repo(config_dir)
    mock_livestatus.add_table(
        "services", [{"host_name": "heute", "description": "CPU load", "state": 0}]
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description state\n"
        "Filter: host_name = heute\nFilter: description = CPU load\nAnd: 2",
        sites=["NO_SITE"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_FORCED_SVC_CHECK;heute;CPU load;...", match_type="ellipsis"
    )

    with set_config(wato_use_git=True), mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/services/actions/reschedule",
            params=json.dumps(
                {"services": [{"site_id": "NO_SITE", "host_name": "heute", "name": "CPU load"}]}
            ),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert setup_git_commit_subjects(config_dir) == ["Initialized GIT for Checkmk"]


@pytest.mark.usefixtures("with_admin_login")
def test_reschedule_checks_waits_as_long_as_configured(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    set_config: SetConfig,
) -> None:
    mock_livestatus.add_table(
        "services", [{"host_name": "heute", "description": "CPU load", "state": 0}]
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description state\n"
        "Filter: host_name = heute\nFilter: description = CPU load\nAnd: 2",
        sites=["NO_SITE"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_FORCED_SVC_CHECK;heute;CPU load;...", match_type="ellipsis"
    )

    with set_config(reschedule_timeout=7.5), mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/services/actions/reschedule",
            params=json.dumps(
                {"services": [{"site_id": "NO_SITE", "host_name": "heute", "name": "CPU load"}]}
            ),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json["wait_timeout"] == 7.5


@pytest.mark.usefixtures("with_admin_login")
def test_reschedule_checks_refuses_services_not_visible_to_the_user(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description state\n"
        "Filter: host_name = heute\nFilter: description = Secret\nAnd: 2",
        sites=["NO_SITE"],
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/services/actions/reschedule",
            params=json.dumps(
                {"services": [{"site_id": "NO_SITE", "host_name": "heute", "name": "Secret"}]}
            ),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            status=HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    assert resp.json["title"] == "None of the services was found"


def test_reschedule_spreads_the_checks_over_the_visible_services_only(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    start = dt.datetime.fromtimestamp(1767225600)
    mock_livestatus.add_table(
        "services",
        [
            {"host_name": "web-01", "description": "CPU load", "state": 0},
            {"host_name": "web-01", "description": "Memory", "state": 0},
        ],
        site="local",
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description state\n"
        "Filter: host_name = web-01\nFilter: description = CPU load\nAnd: 2\n"
        "Filter: host_name = web-01\nFilter: description = Secret\nAnd: 2\n"
        "Filter: host_name = web-01\nFilter: description = Memory\nAnd: 2\nOr: 3",
        sites=["local"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_FORCED_SVC_CHECK;web-01;CPU load;1767225600",
        match_type="ellipsis",
        sites=["local"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_FORCED_SVC_CHECK;web-01;Memory;1767225900",
        match_type="ellipsis",
        sites=["local"],
    )

    with mock_livestatus(expect_status_query=False):
        rescheduled = LiveStatusServiceActions(
            connection=MultiSiteConnection(sites=mock_site_configurations(mock_livestatus.sites))
        ).reschedule(
            [
                ServiceTarget("local", "web-01", "CPU load"),
                ServiceTarget("local", "web-01", "Secret"),
                ServiceTarget("local", "web-01", "Memory"),
            ],
            start=start,
            spread=dt.timedelta(minutes=10),
        )

    assert rescheduled == 2

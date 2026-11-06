#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from http import HTTPStatus

import pytest

from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK

_ACTIONS = "/NO_SITE/check_mk/api/internal/monitor/services/actions"
_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
# Another site monitors a host of the same name, whose service must be left alone.
_REMOTE_CPU = {"site_id": "remote", "host_name": "webserver", "name": "CPU load"}
_VISIBLE_QUERY = (
    "GET services\nColumns: host_name description state\n"
    "Filter: host_name = webserver\nFilter: description = CPU load\nAnd: 2"
)


def _monitor_cpu_on_remote(live: MockLiveStatusConnection, *, state: int) -> None:
    live.add_table(
        "services",
        [{"host_name": "webserver", "description": "CPU load", "state": state}],
        site="remote",
    )
    live.expect_query(_VISIBLE_QUERY, sites=["remote"])


@pytest.mark.usefixtures("with_admin_login")
def test_schedules_the_downtime_on_the_services_own_site_only(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _monitor_cpu_on_remote(mock_livestatus, state=0)
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_SVC_DOWNTIME;webserver;CPU load;...;Maintenance",
        match_type="ellipsis",
        sites=["remote"],
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            f"{_ACTIONS}/schedule_downtime",
            params=json.dumps(
                {
                    "services": [_REMOTE_CPU],
                    "comment": "Maintenance",
                    "start_time": "2026-07-21T17:00:00Z",
                    "end_time": "2026-07-21T19:00:00Z",
                }
            ),
            headers=_HEADERS,
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"scheduled": 1}


@pytest.mark.usefixtures("with_admin_login")
def test_removes_the_downtimes_on_the_services_own_site_only(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
        "downtimes",
        [{"id": 9, "host_name": "webserver", "service_description": "CPU load", "is_service": 1}],
        site="remote",
    )
    mock_livestatus.expect_query(
        "GET downtimes\nColumns: id host_name service_description\nFilter: host_name = webserver\n"
        "Filter: service_description = CPU load\nAnd: 2",
        sites=["remote"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] DEL_SVC_DOWNTIME;9", match_type="ellipsis", sites=["remote"]
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            f"{_ACTIONS}/remove_downtimes",
            params=json.dumps({"services": [_REMOTE_CPU]}),
            headers=_HEADERS,
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"removed": 1}


@pytest.mark.usefixtures("with_admin_login")
def test_removes_no_downtime_of_a_service_selected_only_on_another_site(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
        "downtimes",
        [
            {"id": 1, "host_name": "app", "service_description": "CPU load", "is_service": 1},
            {"id": 2, "host_name": "webserver", "service_description": "CPU load", "is_service": 1},
        ],
        site="NO_SITE",
    )
    mock_livestatus.add_table(
        "downtimes",
        [{"id": 9, "host_name": "webserver", "service_description": "CPU load", "is_service": 1}],
        site="remote",
    )
    mock_livestatus.expect_query(
        "GET downtimes\nColumns: id host_name service_description\n"
        "Filter: host_name = app\nFilter: service_description = CPU load\nAnd: 2\n"
        "Filter: host_name = webserver\nFilter: service_description = CPU load\nAnd: 2\nOr: 2",
        sites=["NO_SITE", "remote"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] DEL_SVC_DOWNTIME;1", match_type="ellipsis", sites=["NO_SITE"]
    )
    mock_livestatus.expect_query(
        "COMMAND [...] DEL_SVC_DOWNTIME;9", match_type="ellipsis", sites=["remote"]
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            f"{_ACTIONS}/remove_downtimes",
            params=json.dumps(
                {
                    "services": [
                        {"site_id": "NO_SITE", "host_name": "app", "name": "CPU load"},
                        _REMOTE_CPU,
                    ]
                }
            ),
            headers=_HEADERS,
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"removed": 2}

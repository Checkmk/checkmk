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
def test_acknowledges_the_service_on_its_own_site_only(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _monitor_cpu_on_remote(mock_livestatus, state=2)
    mock_livestatus.expect_query(
        "COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;webserver;CPU load;1;0;0;...;Working on it;",
        match_type="ellipsis",
        sites=["remote"],
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            f"{_ACTIONS}/acknowledge",
            params=json.dumps({"services": [_REMOTE_CPU], "comment": "Working on it"}),
            headers=_HEADERS,
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"acknowledged": 1}


@pytest.mark.usefixtures("with_admin_login")
def test_removes_the_acknowledgement_on_the_services_own_site_only(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _monitor_cpu_on_remote(mock_livestatus, state=2)
    mock_livestatus.expect_query(
        "COMMAND [...] REMOVE_SVC_ACKNOWLEDGEMENT;webserver;CPU load",
        match_type="ellipsis",
        sites=["remote"],
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            f"{_ACTIONS}/remove_acknowledgements",
            params=json.dumps({"services": [_REMOTE_CPU]}),
            headers=_HEADERS,
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"removed": 1}


@pytest.mark.usefixtures("with_admin_login")
def test_leaves_a_service_without_a_problem_unacknowledged(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _monitor_cpu_on_remote(mock_livestatus, state=0)

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            f"{_ACTIONS}/acknowledge",
            params=json.dumps({"services": [_REMOTE_CPU], "comment": "Working on it"}),
            headers=_HEADERS,
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"acknowledged": 0}


@pytest.mark.usefixtures("with_admin_login")
def test_leaves_a_service_selected_only_on_another_site_unacknowledged(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
        "services",
        [
            {"host_name": "app", "description": "CPU load", "state": 2},
            {"host_name": "webserver", "description": "CPU load", "state": 2},
        ],
        site="NO_SITE",
    )
    mock_livestatus.add_table(
        "services",
        [{"host_name": "webserver", "description": "CPU load", "state": 2}],
        site="remote",
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description state\n"
        "Filter: host_name = app\nFilter: description = CPU load\nAnd: 2\n"
        "Filter: host_name = webserver\nFilter: description = CPU load\nAnd: 2\nOr: 2",
        sites=["NO_SITE", "remote"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;app;CPU load;...",
        match_type="ellipsis",
        sites=["NO_SITE"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;webserver;CPU load;...",
        match_type="ellipsis",
        sites=["remote"],
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            f"{_ACTIONS}/acknowledge",
            params=json.dumps(
                {
                    "services": [
                        {"site_id": "NO_SITE", "host_name": "app", "name": "CPU load"},
                        _REMOTE_CPU,
                    ],
                    "comment": "Working on it",
                }
            ),
            headers=_HEADERS,
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"acknowledged": 2}


@pytest.mark.usefixtures("with_admin_login")
def test_refuses_an_acknowledgement_when_no_service_is_found(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table("services", [], site="remote")
    mock_livestatus.expect_query(_VISIBLE_QUERY, sites=["remote"])

    with mock_livestatus:
        aut_user_auth_wsgi_app.post(
            f"{_ACTIONS}/acknowledge",
            params=json.dumps({"services": [_REMOTE_CPU], "comment": "Working on it"}),
            headers=_HEADERS,
            status=HTTPStatus.UNPROCESSABLE_ENTITY,
        )

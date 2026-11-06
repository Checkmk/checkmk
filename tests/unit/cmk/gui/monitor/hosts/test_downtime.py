#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from http import HTTPStatus

import pytest

from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK

_ACTIONS = "/NO_SITE/check_mk/api/internal/monitor/hosts/actions"
_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
# Another site monitors a host of the same name, which must be left alone.
_REMOTE_WEBSERVER = {"site_id": "remote", "name": "webserver"}
_WINDOW = {"start_time": "2026-07-21T17:00:00Z", "end_time": "2026-07-21T19:00:00Z"}


@pytest.mark.usefixtures("with_admin_login")
def test_schedules_the_downtime_on_the_hosts_own_site_only(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table("hosts", [{"name": "webserver", "state": 0}], site="remote")
    mock_livestatus.expect_query(
        "GET hosts\nColumns: name\nFilter: name = webserver", sites=["remote"]
    )
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_HOST_DOWNTIME;webserver;...;Maintenance",
        match_type="ellipsis",
        sites=["remote"],
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            f"{_ACTIONS}/schedule_downtime",
            params=json.dumps({"hosts": [_REMOTE_WEBSERVER], "comment": "Maintenance", **_WINDOW}),
            headers=_HEADERS,
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"scheduled": 1}


@pytest.mark.usefixtures("with_admin_login")
def test_looks_up_the_child_hosts_on_the_parents_site_only(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
        "hosts",
        [
            {"name": "webserver", "parents": [], "state": 0},
            {"name": "db", "parents": ["webserver"], "state": 0},
        ],
        site="remote",
    )
    mock_livestatus.expect_query(
        "GET hosts\nColumns: name\nFilter: parents >= webserver", sites=["remote"]
    )
    mock_livestatus.expect_query(
        "GET hosts\nColumns: name\nFilter: parents >= db", sites=["remote"]
    )
    mock_livestatus.expect_query(
        "GET hosts\nColumns: name\nFilter: name = webserver\nFilter: name = db\nOr: 2",
        sites=["remote"],
    )
    for host_name in ("webserver", "db"):
        mock_livestatus.expect_query(
            f"COMMAND [...] SCHEDULE_HOST_DOWNTIME;{host_name};...",
            match_type="ellipsis",
            sites=["remote"],
        )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            f"{_ACTIONS}/schedule_downtime",
            params=json.dumps(
                {
                    "hosts": [_REMOTE_WEBSERVER],
                    "comment": "Maintenance",
                    "include_child_hosts": True,
                    **_WINDOW,
                }
            ),
            headers=_HEADERS,
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"scheduled": 2}


@pytest.mark.usefixtures("with_admin_login")
def test_refuses_a_downtime_that_ends_before_it_starts(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    aut_user_auth_wsgi_app.post(
        f"{_ACTIONS}/schedule_downtime",
        params=json.dumps(
            {
                "hosts": [_REMOTE_WEBSERVER],
                "comment": "Maintenance",
                "start_time": _WINDOW["end_time"],
                "end_time": _WINDOW["start_time"],
            }
        ),
        headers=_HEADERS,
        status=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.usefixtures("with_admin_login")
def test_removes_the_downtimes_on_the_hosts_own_site_only(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
        "downtimes",
        [{"id": 7, "host_name": "webserver", "service_description": "", "is_service": 0}],
        site="remote",
    )
    mock_livestatus.expect_query(
        "GET downtimes\nColumns: id host_name\nFilter: is_service = 0\n"
        "Filter: host_name = webserver\nAnd: 2",
        sites=["remote"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] DEL_HOST_DOWNTIME;7", match_type="ellipsis", sites=["remote"]
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            f"{_ACTIONS}/remove_downtimes",
            params=json.dumps({"hosts": [_REMOTE_WEBSERVER]}),
            headers=_HEADERS,
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"removed": 1}


@pytest.mark.usefixtures("with_admin_login")
def test_removes_no_downtime_of_a_host_selected_only_on_another_site(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
        "downtimes",
        [
            {"id": 1, "host_name": "app", "service_description": "", "is_service": 0},
            {"id": 2, "host_name": "webserver", "service_description": "", "is_service": 0},
        ],
        site="NO_SITE",
    )
    mock_livestatus.add_table(
        "downtimes",
        [{"id": 7, "host_name": "webserver", "service_description": "", "is_service": 0}],
        site="remote",
    )
    mock_livestatus.expect_query(
        "GET downtimes\nColumns: id host_name\nFilter: is_service = 0\n"
        "Filter: host_name = app\nFilter: host_name = webserver\nOr: 2\nAnd: 2",
        sites=["NO_SITE", "remote"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] DEL_HOST_DOWNTIME;1", match_type="ellipsis", sites=["NO_SITE"]
    )
    mock_livestatus.expect_query(
        "COMMAND [...] DEL_HOST_DOWNTIME;7", match_type="ellipsis", sites=["remote"]
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            f"{_ACTIONS}/remove_downtimes",
            params=json.dumps(
                {"hosts": [{"site_id": "NO_SITE", "name": "app"}, _REMOTE_WEBSERVER]}
            ),
            headers=_HEADERS,
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"removed": 2}

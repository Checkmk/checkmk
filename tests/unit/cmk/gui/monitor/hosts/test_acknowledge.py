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
_VISIBLE_QUERY = "GET hosts\nColumns: name\nFilter: name = webserver"


def _monitor_webserver_on_remote(live: MockLiveStatusConnection) -> None:
    live.add_table("hosts", [{"name": "webserver"}], site="remote")
    live.expect_query(_VISIBLE_QUERY, sites=["remote"])


@pytest.mark.usefixtures("with_admin_login")
def test_acknowledges_the_host_on_its_own_site_only(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _monitor_webserver_on_remote(mock_livestatus)
    mock_livestatus.expect_query(
        "COMMAND [...] ACKNOWLEDGE_HOST_PROBLEM;webserver;2;1;1;...;Working on it;",
        match_type="ellipsis",
        sites=["remote"],
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            f"{_ACTIONS}/acknowledge",
            params=json.dumps(
                {
                    "hosts": [_REMOTE_WEBSERVER],
                    "comment": "Working on it",
                    "sticky": True,
                    "persistent": True,
                    "notify": True,
                }
            ),
            headers=_HEADERS,
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"acknowledged": 1}


@pytest.mark.usefixtures("with_admin_login")
def test_removes_the_acknowledgement_on_the_hosts_own_site_only(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _monitor_webserver_on_remote(mock_livestatus)
    mock_livestatus.expect_query(
        "COMMAND [...] REMOVE_HOST_ACKNOWLEDGEMENT;webserver",
        match_type="ellipsis",
        sites=["remote"],
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            f"{_ACTIONS}/remove_acknowledgements",
            params=json.dumps({"hosts": [_REMOTE_WEBSERVER]}),
            headers=_HEADERS,
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"removed": 1}


@pytest.mark.usefixtures("with_admin_login")
def test_sends_nothing_for_a_host_the_user_does_not_see(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    # Livestatus answers only with the hosts the user may see.
    mock_livestatus.add_table("hosts", [], site="remote")
    mock_livestatus.expect_query(_VISIBLE_QUERY, sites=["remote"])

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            f"{_ACTIONS}/remove_acknowledgements",
            params=json.dumps({"hosts": [_REMOTE_WEBSERVER]}),
            headers=_HEADERS,
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"removed": 0}


@pytest.mark.usefixtures("with_admin_login")
def test_refuses_an_acknowledgement_without_a_comment(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    aut_user_auth_wsgi_app.post(
        f"{_ACTIONS}/acknowledge",
        params=json.dumps({"hosts": [_REMOTE_WEBSERVER], "comment": ""}),
        headers=_HEADERS,
        status=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.usefixtures("with_admin_login")
def test_leaves_a_host_selected_only_on_another_site_unacknowledged(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table("hosts", [{"name": "app"}, {"name": "webserver"}], site="NO_SITE")
    mock_livestatus.add_table("hosts", [{"name": "webserver"}], site="remote")
    mock_livestatus.expect_query(
        "GET hosts\nColumns: name\nFilter: name = app\nFilter: name = webserver\nOr: 2",
        sites=["NO_SITE", "remote"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] ACKNOWLEDGE_HOST_PROBLEM;app;...",
        match_type="ellipsis",
        sites=["NO_SITE"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] ACKNOWLEDGE_HOST_PROBLEM;webserver;...",
        match_type="ellipsis",
        sites=["remote"],
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            f"{_ACTIONS}/acknowledge",
            params=json.dumps(
                {
                    "hosts": [{"site_id": "NO_SITE", "name": "app"}, _REMOTE_WEBSERVER],
                    "comment": "Working on it",
                }
            ),
            headers=_HEADERS,
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"acknowledged": 2}


@pytest.mark.usefixtures("with_admin_login")
def test_refuses_an_acknowledgement_when_no_host_is_found(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table("hosts", [], site="remote")
    mock_livestatus.expect_query(_VISIBLE_QUERY, sites=["remote"])

    with mock_livestatus:
        aut_user_auth_wsgi_app.post(
            f"{_ACTIONS}/acknowledge",
            params=json.dumps({"hosts": [_REMOTE_WEBSERVER], "comment": "Working on it"}),
            headers=_HEADERS,
            status=HTTPStatus.UNPROCESSABLE_ENTITY,
        )

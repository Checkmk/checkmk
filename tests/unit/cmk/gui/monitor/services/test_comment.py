#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from http import HTTPStatus

import pytest

from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK

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
def test_adds_the_comment_on_the_services_own_site_only(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _monitor_cpu_on_remote(mock_livestatus, state=0)
    mock_livestatus.expect_query(
        "COMMAND [...] ADD_SVC_COMMENT;webserver;CPU load;1;...;Disk swap planned",
        match_type="ellipsis",
        sites=["remote"],
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/services/actions/add_comment",
            params=json.dumps(
                {
                    # Another site monitors a host of the same name, whose service must be left
                    # alone.
                    "services": [
                        {"site_id": "remote", "host_name": "webserver", "name": "CPU load"}
                    ],
                    "comment": "Disk swap planned",
                }
            ),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"commented": 1}

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from http import HTTPStatus

import pytest

from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK


@pytest.mark.usefixtures("with_admin_login")
def test_adds_the_comment_on_the_hosts_own_site_only(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table("hosts", [{"name": "webserver", "state": 0}], site="remote")
    mock_livestatus.expect_query(
        "GET hosts\nColumns: name\nFilter: name = webserver", sites=["remote"]
    )
    mock_livestatus.expect_query(
        "COMMAND [...] ADD_HOST_COMMENT;webserver;1;...;Disk swap planned",
        match_type="ellipsis",
        sites=["remote"],
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/hosts/actions/add_comment",
            params=json.dumps(
                {
                    # Another site monitors a host of the same name, which must be left alone.
                    "hosts": [{"site_id": "remote", "name": "webserver"}],
                    "comment": "Disk swap planned",
                }
            ),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"commented": 1}

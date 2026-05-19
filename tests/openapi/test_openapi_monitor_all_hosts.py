#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.user import UserId
from tests.testlib.rest_api_client import ClientRegistry


class TestMonitorHostsAuth:
    def test_valid_credentials(self, clients: ClientRegistry) -> None:
        assert clients.MonitorHosts.list_all(limit=100).status_code == 200

    def test_invalid_credentials(self, clients: ClientRegistry) -> None:
        client = clients.MonitorHosts
        client.set_credentials("foouser", "barpassword")

        resp = client.list_all(limit=100, expect_ok=False)

        assert resp.status_code == 401
        assert "credentials" in resp.json["detail"]

    def test_insufficient_permissions(
        self, clients: ClientRegistry, with_user: tuple[UserId, str]
    ) -> None:
        client = clients.MonitorHosts
        client.set_credentials(*with_user)

        resp = client.list_all(limit=100, expect_ok=False)

        assert resp.status_code == 401
        assert "permission" in resp.json["detail"]

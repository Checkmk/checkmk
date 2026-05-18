#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.user import UserId
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.rest_api_client import ClientRegistry


class TestMonitorHostsAuth:
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


class TestMonitorHostsResponse:
    @property
    def limit(self) -> int:
        return 1000

    @property
    def hosts(self) -> list[dict[str, str | int]]:
        return [
            {
                "name": "heute",
                "address": "127.0.0.1",
                "alias": "Today",
                "state": 0,
                "num_services": 0,
                "num_services_ok": 0,
                "num_services_warn": 0,
                "num_services_crit": 0,
                "num_services_unknown": 0,
                "num_services_pending": 0,
            },
            {
                "name": "gestern",
                "address": "127.0.10.1",
                "alias": "Yesterday",
                "state": 1,
                "num_services": 0,
                "num_services_ok": 0,
                "num_services_warn": 0,
                "num_services_crit": 0,
                "num_services_unknown": 0,
                "num_services_pending": 0,
            },
            {
                "name": "morgen",
                "address": "127.0.2.1",
                "alias": "Tomorrow",
                "state": 2,
                "num_services": 0,
                "num_services_ok": 0,
                "num_services_warn": 0,
                "num_services_crit": 0,
                "num_services_unknown": 0,
                "num_services_pending": 0,
            },
        ]

    def test_hosts(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        self._setup_host_table(mock_livestatus)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=self.limit)

        value = resp.json["hosts"]
        expected = [
            {
                "alias": "Today",
                "ip": "127.0.0.1",
                "name": "heute",
                "num_services": 0,
                "num_services_crit": 0,
                "num_services_ok": 0,
                "num_services_pending": 0,
                "num_services_unknown": 0,
                "num_services_warn": 0,
                "site_id": "NO_SITE",
                "state": "UP",
            },
            {
                "alias": "Yesterday",
                "ip": "127.0.10.1",
                "name": "gestern",
                "num_services": 0,
                "num_services_crit": 0,
                "num_services_ok": 0,
                "num_services_pending": 0,
                "num_services_unknown": 0,
                "num_services_warn": 0,
                "site_id": "NO_SITE",
                "state": "DOWN",
            },
            {
                "alias": "Tomorrow",
                "ip": "127.0.2.1",
                "name": "morgen",
                "num_services": 0,
                "num_services_crit": 0,
                "num_services_ok": 0,
                "num_services_pending": 0,
                "num_services_unknown": 0,
                "num_services_warn": 0,
                "site_id": "NO_SITE",
                "state": "UNREACHABLE",
            },
        ]

        assert value == expected

    def test_metadata(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        self._setup_host_table(mock_livestatus)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=self.limit)

        value = resp.json["meta"]
        expected = {"limit": self.limit, "total": 3}

        assert value == expected

    def _setup_host_table(self, mock_livestatus: MockLiveStatusConnection) -> None:
        # Add the hosts defined in the fixture to the mock livestatus "hosts" table.
        mock_livestatus.add_table("hosts", self.hosts)

        # Need to update the number of host counts to reflect the fixture.
        for row in mock_livestatus.tables["status"][mock_livestatus.sites[0]]:
            row["num_hosts"] = len(self.hosts)

        # Register the livestatus queries that we expect are endpoint to call.
        mock_livestatus.expect_query(
            [
                "GET hosts",
                "Columns: name alias address state num_services num_services_ok num_services_warn num_services_crit num_services_unknown num_services_pending",
                f"Limit: {self.limit}",
            ]
        )
        mock_livestatus.expect_query(
            [
                "GET status",
                "Columns: num_hosts",
            ]
        )

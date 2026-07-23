#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import time_machine

from cmk.ccc.user import UserId
from cmk.gui.monitor.services._api._list_host_services import _MAX_HOST_SVC_LIMIT
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.rest_api_client import ClientRegistry


class TestMonitorHostServicesAuth:
    def test_invalid_credentials(self, clients: ClientRegistry) -> None:
        client = clients.MonitorHosts
        client.set_credentials("foouser", "barpassword")

        resp = client.list_host_services(
            hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT, expect_ok=False
        )

        assert resp.status_code == 401
        assert "credentials" in resp.json["detail"]

    def test_normal_user_is_permitted(
        self,
        clients: ClientRegistry,
        with_user: tuple[UserId, str],
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        client = clients.MonitorHosts
        client.set_credentials(*with_user)

        mock_livestatus.add_table("hosts", [])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                "Columns: name",
                f"Filter: name = {_HOSTNAME}",
                "Limit: 1",
            ],
            sites=[_SITE_ID],
            match_type="loose",
        )

        with mock_livestatus(expect_status_query=True):
            resp = client.list_host_services(
                hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT, expect_ok=False
            )

        assert resp.status_code == 404


class TestMonitorHostServicesQueryParamValidation:
    def test_unknown_site_is_rejected(self, clients: ClientRegistry) -> None:
        resp = clients.MonitorHosts.list_host_services(
            hostname=_HOSTNAME, site_id="no-such-site", limit=_LIMIT, expect_ok=False
        )
        assert resp.status_code == 400


class TestMonitorHostServices:
    def test_missing_host_returns_404(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", [])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                "Columns: name",
                "Filter: name = no-such-host",
                "Limit: 1",
            ],
            sites=[_SITE_ID],
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_host_services(
                hostname="no-such-host", site_id=_SITE_ID, limit=_LIMIT, expect_ok=False
            )

        assert resp.status_code == 404

    @time_machine.travel("2026-07-13 11:39:00+00:00", tick=False)
    def test_services(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", [{"name": _HOSTNAME}])
        mock_livestatus.add_table(
            "services",
            [
                {
                    "description": "CPU load",
                    "host_name": _HOSTNAME,
                    "state": 0,
                    "plugin_output": "OK - load average: 0.10, 0.05, 0.01",
                    "last_check": time.time() - 30,
                    "last_state_change": time.time(),
                }
            ],
        )
        mock_livestatus.expect_query(
            [
                "GET hosts",
                "Columns: name",
                f"Filter: name = {_HOSTNAME}",
                "Limit: 1",
            ],
            sites=[_SITE_ID],
        )
        mock_livestatus.expect_query(
            [
                "GET services",
                f"Columns: {_SERVICES_COLUMNS}",
                f"Filter: host_name = {_HOSTNAME}",
                f"Limit: {_LIMIT}",
            ],
            sites=[_SITE_ID],
        )
        mock_livestatus.expect_query(
            [
                "GET services",
                "Stats: state >= 0",
                f"Filter: host_name = {_HOSTNAME}",
            ],
            sites=[_SITE_ID],
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_host_services(
                hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT
            )

        assert resp.json == {
            "services": [
                {
                    "name": "CPU load",
                    "state": "OK",
                    "summary": "OK - load average: 0.10, 0.05, 0.01",
                    "last_check": "2026-07-13T11:38:30Z",
                    "last_state_change": "2026-07-13T11:39:00Z",
                }
            ],
            "meta": {
                "hostname": _HOSTNAME,
                "site_id": _SITE_ID,
                "limit": _LIMIT,
                "matched": 1,
                "total": 1,
            },
        }

    def test_services_without_limit(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", [{"name": _HOSTNAME}])
        mock_livestatus.add_table(
            "services",
            [
                {
                    "description": "CPU load",
                    "host_name": _HOSTNAME,
                    "state": 0,
                    "plugin_output": "OK - load average: 0.10, 0.05, 0.01",
                    "last_check": time.time(),
                    "last_state_change": time.time(),
                }
            ],
        )
        mock_livestatus.expect_query(
            [
                "GET hosts",
                "Columns: name",
                f"Filter: name = {_HOSTNAME}",
                "Limit: 1",
            ],
            sites=[_SITE_ID],
        )
        mock_livestatus.expect_query(
            [
                "GET services",
                f"Columns: {_SERVICES_COLUMNS}",
                f"Filter: host_name = {_HOSTNAME}",
            ],
            sites=[_SITE_ID],
        )
        mock_livestatus.expect_query(
            [
                "GET services",
                "Stats: state >= 0",
                f"Filter: host_name = {_HOSTNAME}",
            ],
            sites=[_SITE_ID],
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_host_services(
                hostname=_HOSTNAME, site_id=_SITE_ID, limit=None
            )

        assert len(resp.json["services"]) == 1
        assert resp.json["meta"]["limit"] is None


class TestMonitorHostServicessLimitPermissions:
    def test_limit_removal_clamped_without_permission(
        self,
        clients: ClientRegistry,
        with_user: tuple[UserId, str],
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        client = clients.MonitorHosts
        client.set_credentials(*with_user)

        mock_livestatus.add_table("hosts", [{"name": _HOSTNAME}])
        mock_livestatus.add_table(
            "services",
            [
                {
                    "description": "CPU load",
                    "host_name": _HOSTNAME,
                    "state": 0,
                    "plugin_output": "OK - load average: 0.10, 0.05, 0.01",
                    "last_check": time.time(),
                    "last_state_change": time.time(),
                }
            ],
        )
        # see_all-less user → sites.live() adds an AuthUser line; match loosely to tolerate it.
        mock_livestatus.expect_query(
            [
                "GET hosts",
                "Columns: name",
                f"Filter: name = {_HOSTNAME}",
                "Limit: 1",
            ],
            sites=[_SITE_ID],
            match_type="loose",
        )
        mock_livestatus.expect_query(
            [
                "GET services",
                f"Columns: {_SERVICES_COLUMNS}",
                f"Filter: host_name = {_HOSTNAME}",
                f"Limit: {_MAX_HOST_SVC_LIMIT}",
            ],
            sites=[_SITE_ID],
            match_type="loose",
        )
        mock_livestatus.expect_query(
            [
                "GET services",
                "Stats: state >= 0",
                f"Filter: host_name = {_HOSTNAME}",
            ],
            sites=[_SITE_ID],
            match_type="loose",
        )

        with mock_livestatus(expect_status_query=True):
            resp = client.list_host_services(hostname=_HOSTNAME, site_id=_SITE_ID, limit=None)

        assert resp.json["meta"]["limit"] == _MAX_HOST_SVC_LIMIT

    def test_limit_removal_honored_with_permission(
        self,
        clients: ClientRegistry,
        with_admin: tuple[UserId, str],
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        client = clients.MonitorHosts
        client.set_credentials(*with_admin)

        mock_livestatus.add_table("hosts", [{"name": _HOSTNAME}])
        mock_livestatus.add_table(
            "services",
            [
                {
                    "description": "CPU load",
                    "host_name": _HOSTNAME,
                    "state": 0,
                    "plugin_output": "OK - load average: 0.10, 0.05, 0.01",
                    "last_check": time.time(),
                    "last_state_change": time.time(),
                }
            ],
        )
        mock_livestatus.expect_query(
            [
                "GET hosts",
                "Columns: name",
                f"Filter: name = {_HOSTNAME}",
                "Limit: 1",
            ],
            sites=[_SITE_ID],
            match_type="loose",
        )
        mock_livestatus.expect_query(
            [
                "GET services",
                f"Columns: {_SERVICES_COLUMNS}",
                f"Filter: host_name = {_HOSTNAME}",
            ],
            sites=[_SITE_ID],
            match_type="loose",
        )
        mock_livestatus.expect_query(
            [
                "GET services",
                "Stats: state >= 0",
                f"Filter: host_name = {_HOSTNAME}",
            ],
            sites=[_SITE_ID],
            match_type="loose",
        )

        with mock_livestatus(expect_status_query=True):
            resp = client.list_host_services(hostname=_HOSTNAME, site_id=_SITE_ID, limit=None)

        assert resp.json["meta"]["limit"] is None


_SITE_ID = "NO_SITE"
_HOSTNAME = "heute"
_LIMIT = 1000
_SERVICES_COLUMNS = "description host_name state plugin_output last_check last_state_change"

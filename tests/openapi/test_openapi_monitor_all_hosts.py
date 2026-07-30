#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest
import time_machine

from cmk.ccc.user import UserId
from cmk.gui.monitor.hosts._api._list_hosts import _MAX_NUMBER_OF_HOSTS
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.rest_api_client import ClientRegistry

_SITE_ID = "NO_SITE"

# NOTE: we are a bit contrained on what we can do with the mock livestatus fixture. For instance
# limits and the ``Stats`` meta counts are not faithfully reflected by the mock. Therefore, this
# module mainly tests that the livestatus queries are correctly built based on the user input.


class TestMonitorHostsAuth:
    def test_invalid_credentials(self, clients: ClientRegistry) -> None:
        client = clients.MonitorHosts
        client.set_credentials("foouser", "barpassword")

        resp = client.list_all(limit=100, expect_ok=False)

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

        mock_livestatus.add_table("hosts", _HOSTS)
        # see_all-less user → sites.live() adds an AuthUser line; match loosely to tolerate it.
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ],
            match_type="loose",
        )
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"], match_type="loose")

        with mock_livestatus(expect_status_query=True):
            resp = client.list_all(limit=_LIMIT)

        assert resp.status_code == 200


class TestMonitorHostsQueryParamValidation:
    def test_limit_lower_bound(self, clients: ClientRegistry) -> None:
        resp = clients.MonitorHosts.list_all(limit=-1, expect_ok=False)
        assert resp.status_code == 400

    def test_limit_upper_bound(self, clients: ClientRegistry) -> None:
        resp = clients.MonitorHosts.list_all(limit=1_000_000, expect_ok=False)
        assert resp.status_code == 400

    @pytest.mark.parametrize(
        "sort",
        [
            pytest.param(["nameasc"], id="missing colon separator"),
            pytest.param(["invalid:asc"], id="invalid column"),
            pytest.param(["name:invalid"], id="invalid direction"),
        ],
    )
    def test_invalid_sort_params(self, clients: ClientRegistry, sort: list[str]) -> None:
        resp = clients.MonitorHosts.list_all(limit=100, sort=sort, expect_ok=False)
        assert resp.status_code == 400

    @pytest.mark.parametrize(
        "filters",
        [
            pytest.param({}, id="empty payload"),
            pytest.param(
                {"type": "condition", "field": "states", "op": "one_of", "value": []},
                id="min length of 'one_of' condition",
            ),
            pytest.param(
                {"type": "condition", "field": "states", "op": "one_of", "value": ["UP", "UP"]},
                id="uniqueness in 'one_of' condition",
            ),
            pytest.param(
                {
                    "type": "and",
                    "children": [
                        {"type": "condition", "field": "num_services", "op": "lte", "value": 10},
                    ],
                },
                id="min length of 'and' condition",
            ),
            pytest.param(
                {
                    "type": "and",
                    "children": [
                        {"type": "condition", "field": "num_services", "op": "lte", "value": 10},
                    ],
                },
                id="min length of 'or' condition",
            ),
        ],
    )
    def test_filters_validation_errors(
        self,
        clients: ClientRegistry,
        filters: dict[str, object],
    ) -> None:
        resp = clients.MonitorHosts.list_all(limit=1000, filters=filters, expect_ok=False)
        assert resp.status_code == 400


class TestMonitorHosts:
    def test_hosts(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT)

        assert len(resp.json["hosts"]) == len(_HOSTS)

    def test_hosts_without_limit(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
            ]
        )
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=None)

        assert len(resp.json["hosts"]) == len(_HOSTS)
        assert resp.json["meta"]["limit"] is None


class TestMonitorHostsLimitPermissions:
    def test_limit_removal_clamped_without_permission(
        self,
        clients: ClientRegistry,
        with_user: tuple[UserId, str],
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        client = clients.MonitorHosts
        client.set_credentials(*with_user)

        mock_livestatus.add_table("hosts", _HOSTS)
        # see_all-less user → sites.live() adds an AuthUser line; match loosely to tolerate it.
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_MAX_NUMBER_OF_HOSTS}",
            ],
            match_type="loose",
        )
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"], match_type="loose")

        with mock_livestatus(expect_status_query=True):
            resp = client.list_all(limit=None)

        assert resp.json["meta"]["limit"] == _MAX_NUMBER_OF_HOSTS

    def test_limit_removal_honored_with_permission(
        self,
        clients: ClientRegistry,
        with_admin: tuple[UserId, str],
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        client = clients.MonitorHosts
        client.set_credentials(*with_admin)

        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
            ]
        )
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])

        with mock_livestatus(expect_status_query=True):
            resp = client.list_all(limit=None)

        assert resp.json["meta"]["limit"] is None


class TestMonitorHostsQuery:
    @pytest.mark.parametrize("query", ["", "   "])
    def test_blank_search_is_treated_as_no_filter(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
        query: str,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT, q=query)

        assert len(resp.json["hosts"]) == len(_HOSTS)

    def test_search_with_no_matches(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "Filter: name ~~ no-such-host",
                "Filter: alias ~~ no-such-host",
                "Filter: address ~~ no-such-host",
                "Or: 3",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                "Stats: state >= 0",
                "Filter: name ~~ no-such-host",
                "Filter: alias ~~ no-such-host",
                "Filter: address ~~ no-such-host",
                "Or: 3",
            ]
        )
        with mock_livestatus():
            resp = clients.MonitorHosts.list_all(limit=_LIMIT, q="no-such-host")

        assert len(resp.json["hosts"]) == 0


class TestMonitorHostsFilters:
    def test_filters(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "Filter: num_services <= 10",
                "Filter: state = 0",
                "Filter: state = 1",
                "Or: 2",
                "And: 2",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                "Stats: state >= 0",
                "Filter: num_services <= 10",
                "Filter: state = 0",
                "Filter: state = 1",
                "Or: 2",
                "And: 2",
            ]
        )
        filters = {
            "type": "and",
            "children": [
                {
                    "type": "condition",
                    "field": "num_services",
                    "op": "lte",
                    "value": 10,
                },
                {
                    "type": "condition",
                    "field": "state",
                    "op": "one_of",
                    "value": ["UP", "DOWN"],
                },
            ],
        }
        with mock_livestatus():
            resp = clients.MonitorHosts.list_all(limit=_LIMIT, filters=filters)

        assert resp.json["hosts"] == [
            {
                "address": "127.0.0.1",
                "name": "heute",
                "num_services": 10,
                "num_services_crit": 0,
                "num_services_ok": 10,
                "num_services_pending": 0,
                "num_services_unknown": 0,
                "num_services_warn": 0,
                "site_id": "NO_SITE",
                "state": "UP",
                "legacy_host_status_link": "view.py?view_name=hoststatus&site=NO_SITE&host=heute",
            },
        ]


class TestMonitorHostsFields:
    def test_non_default_field_omitted(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT)

        host = next(h for h in resp.json["hosts"] if h["name"] == "heute")

        assert _NON_DEFAULT_FIELD not in host
        assert _NON_DEFAULT_FIELD not in resp.json["meta"]["fields"]

    def test_non_default_field_specified(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT, fields=[_NON_DEFAULT_FIELD])

        host = next(h for h in resp.json["hosts"] if h["name"] == "heute")

        assert _NON_DEFAULT_FIELD in host
        assert _NON_DEFAULT_FIELD in resp.json["meta"]["fields"]

    def test_all_optional_fields_specified(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])

        optional_fields = [
            "alias",
            "folder",
            "last_check",
            "last_state_change",
        ]

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT, fields=optional_fields)

        host = next(h for h in resp.json["hosts"] if h["name"] == "heute")

        assert all(field in host for field in optional_fields)


class TestMonitorHostOverviewAuth:
    def test_invalid_credentials(self, clients: ClientRegistry) -> None:
        client = clients.MonitorHosts
        client.set_credentials("foouser", "barpassword")

        resp = client.get(hostname="heute", site_id=_SITE_ID, expect_ok=False)

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
        # see_all-less user → sites.live() adds an AuthUser line; match loosely to tolerate it.
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_OVERVIEW_COLUMNS}",
                "Filter: name = heute",
            ],
            sites=[_SITE_ID],
            match_type="loose",
        )

        with mock_livestatus(expect_status_query=True):
            resp = client.get(hostname="heute", site_id=_SITE_ID, expect_ok=False)

        assert resp.status_code == 404


class TestMonitorHostOverviewQueryParamValidation:
    def test_unknown_site_is_rejected(self, clients: ClientRegistry) -> None:
        resp = clients.MonitorHosts.get(hostname="heute", site_id="no-such-site", expect_ok=False)
        assert resp.status_code == 400


class TestMonitorHostActionMenuAuth:
    def test_invalid_credentials(self, clients: ClientRegistry) -> None:
        client = clients.MonitorHosts
        client.set_credentials("foouser", "barpassword")

        resp = client.action_menu(hostname="heute", site_id=_SITE_ID, expect_ok=False)

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
        # see_all-less user → sites.live() adds an AuthUser line; match loosely to tolerate it
        # (and the dynamic icon-painter column list).
        mock_livestatus.expect_query(
            [
                "GET hosts",
                "Filter: host_name = heute",
                "ColumnHeaders: off",
            ],
            match_type="loose",
            sites=[_SITE_ID],
        )

        with mock_livestatus(expect_status_query=True):
            resp = client.action_menu(hostname="heute", site_id=_SITE_ID, expect_ok=False)

        assert resp.status_code == 404


class TestMonitorHostActionMenuQueryParamValidation:
    def test_unknown_site_is_rejected(self, clients: ClientRegistry) -> None:
        resp = clients.MonitorHosts.action_menu(
            hostname="heute", site_id="no-such-site", expect_ok=False
        )
        assert resp.status_code == 400


class TestMonitorHostActionMenu:
    def test_missing_host_returns_404(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", [])
        mock_livestatus.expect_query(
            "GET hosts\nColumns: ...\nFilter: host_name = no-such-host\nColumnHeaders: off",
            match_type="ellipsis",
            sites=[_SITE_ID],
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.action_menu(
                hostname="no-such-host", site_id=_SITE_ID, expect_ok=False
            )

        assert resp.status_code == 404


class TestMonitorHostOverview:
    @time_machine.travel("2026-07-13 11:39:00+00:00", tick=False)
    def test_get_host_overview(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table(
            "hosts",
            [
                {
                    "name": "heute",
                    "alias": "Today",
                    "address": "127.0.0.1",
                    "state": 0,
                    "num_services": 10,
                    "num_services_ok": 10,
                    "num_services_warn": 0,
                    "num_services_crit": 0,
                    "num_services_unknown": 0,
                    "num_services_pending": 0,
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "last_check": time.time() - 30,
                    "last_state_change": time.time(),
                    "tags": {"criticality": "prod"},
                    "labels": {"cmk/os_family": "linux"},
                    "label_sources": {"cmk/os_family": "discovered"},
                    "custom_variables": {"CUSTOMER": "customer1"},
                    "contact_groups": ["all"],
                    "filename": "/wato/network/switches/hosts.mk",
                }
            ],
        )
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_OVERVIEW_COLUMNS}",
                "Filter: name = heute",
            ],
            sites=[_SITE_ID],
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get(hostname="heute", site_id=_SITE_ID)

        assert resp.json == {
            "name": "heute",
            "alias": "Today",
            "address": "127.0.0.1",
            "state": "UP",
            "site_id": "NO_SITE",
            "site_alias": "Local site NO_SITE",
            "service_counts": {
                "total": 10,
                "ok": 10,
                "warn": 0,
                "crit": 0,
                "unknown": 0,
                "pending": 0,
            },
            "modes": [],
            "last_check": "2026-07-13T11:38:30Z",
            "last_state_change": "2026-07-13T11:39:00Z",
            "customer": "customer1",
            "folder": "/network/switches",
            "contact_groups": ["all"],
            "tags": {"criticality": "prod"},
            "labels": {"cmk/os_family": {"value": "linux", "source": "discovered"}},
            "legacy_host_status_link": "view.py?view_name=hoststatus&site=NO_SITE&host=heute",
        }

    @time_machine.travel("2026-07-13 11:39:00+00:00", tick=False)
    def test_get_host_overview_no_customer(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table(
            "hosts",
            [
                {
                    "name": "heute",
                    "alias": "Today",
                    "address": "127.0.0.1",
                    "state": 0,
                    "num_services": 0,
                    "num_services_ok": 0,
                    "num_services_warn": 0,
                    "num_services_crit": 0,
                    "num_services_unknown": 0,
                    "num_services_pending": 0,
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "last_check": time.time(),
                    "last_state_change": time.time(),
                    "contact_groups": [],
                    "tags": {},
                    "labels": {},
                    "label_sources": {},
                    "custom_variables": {},
                    "filename": "",
                }
            ],
        )
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_OVERVIEW_COLUMNS}",
                "Filter: name = heute",
            ],
            sites=[_SITE_ID],
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get(hostname="heute", site_id=_SITE_ID)

        assert resp.json["customer"] is None

    def test_get_host_overview_not_found(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", [])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_OVERVIEW_COLUMNS}",
                "Filter: name = no-such-host",
            ],
            sites=[_SITE_ID],
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get(
                hostname="no-such-host", site_id=_SITE_ID, expect_ok=False
            )

        assert resp.status_code == 404


class TestMonitorHostsReschedule:
    def test_reschedule_sends_forced_check_command(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(
            "COMMAND [...] SCHEDULE_FORCED_HOST_CHECK;heute;...", match_type="ellipsis"
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.reschedule(hosts=[{"site_id": "NO_SITE", "name": "heute"}])

        assert resp.json["rescheduled"] == 1

    def test_reschedule_sends_one_command_per_host(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(
            "COMMAND [...] SCHEDULE_FORCED_HOST_CHECK;heute;...", match_type="ellipsis"
        )
        mock_livestatus.expect_query(
            "COMMAND [...] SCHEDULE_FORCED_HOST_CHECK;gestern;...", match_type="ellipsis"
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.reschedule(
                hosts=[
                    {"site_id": "NO_SITE", "name": "heute"},
                    {"site_id": "NO_SITE", "name": "gestern"},
                ],
                spread_minutes=5,
            )

        assert resp.json["rescheduled"] == 2


_LIMIT = 1000
_NON_DEFAULT_FIELD = "alias"
_HOSTS = [
    {
        "name": "heute",
        "address": "127.0.0.1",
        "alias": "Today",
        "state": 0,
        "num_services": 10,
        "num_services_ok": 10,
        "num_services_warn": 0,
        "num_services_crit": 0,
        "num_services_unknown": 0,
        "num_services_pending": 0,
        "acknowledged": 0,
        "scheduled_downtime_depth": 0,
        "last_check": 1700000000,
        "last_state_change": 1700000060,
        "filename": "/wato/hosts.mk",
    },
    {
        "name": "gestern",
        "address": "127.0.10.1",
        "alias": "Yesterday",
        "state": 1,
        "num_services": 20,
        "num_services_ok": 20,
        "num_services_warn": 0,
        "num_services_crit": 0,
        "num_services_unknown": 0,
        "num_services_pending": 0,
        "acknowledged": 0,
        "scheduled_downtime_depth": 0,
        "last_check": 1700000100,
        "last_state_change": 1700000160,
        "filename": "/wato/network/hosts.mk",
    },
    {
        "name": "morgen",
        "address": "127.0.2.1",
        "alias": "Tomorrow",
        "state": 2,
        "num_services": 30,
        "num_services_ok": 30,
        "num_services_warn": 0,
        "num_services_crit": 0,
        "num_services_unknown": 0,
        "num_services_pending": 0,
        "acknowledged": 0,
        "scheduled_downtime_depth": 0,
        "last_check": 1700000200,
        "last_state_change": 1700000260,
        # Not managed via Setup, e.g. added directly to the monitoring core.
        "filename": "/omd/sites/heute/etc/nagios/conf.d/hosts.mk",
    },
]
_HOST_TABLE_COLUMNS = "name alias address state num_services num_services_ok num_services_warn num_services_crit num_services_unknown num_services_pending acknowledged scheduled_downtime_depth last_check last_state_change filename"
_HOST_OVERVIEW_COLUMNS = "name alias address state num_services num_services_ok num_services_warn num_services_crit num_services_unknown num_services_pending acknowledged scheduled_downtime_depth last_check last_state_change contact_groups tags labels label_sources custom_variables filename"

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.user import UserId
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.rest_api_client import ClientRegistry

# NOTE: we are a bit contrained on what we can do with the mock livestatus fixture. For instance the
# stats table does not get updated when adding hosts. So, the limit and meta data counts will not
# work as expected. Therefore, this module mainly tests that the livestatus are correctly built
# based on the user input.


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

        assert resp.status_code == 403
        assert "permission" in resp.json["detail"]


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
                "OrderBy: name asc",
                f"Limit: {_LIMIT}",
            ]
        )
        mock_livestatus.expect_query(["GET status", "Columns: num_hosts"])

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT)

        assert len(resp.json["hosts"]) == len(_HOSTS)


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
                "OrderBy: name asc",
                f"Limit: {_LIMIT}",
            ]
        )
        mock_livestatus.expect_query(["GET status", "Columns: num_hosts"])

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
                "OrderBy: name asc",
                f"Limit: {_LIMIT}",
            ]
        )
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
                "OrderBy: name asc",
                f"Limit: {_LIMIT}",
            ]
        )
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
                "alias": "Today",
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
            },
        ]


_LIMIT = 1000
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
    },
]
_HOST_TABLE_COLUMNS = "name alias address state num_services num_services_ok num_services_warn num_services_crit num_services_unknown num_services_pending"

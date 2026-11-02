#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from http import HTTPStatus

import pytest
import time_machine

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.monitor.hosts._api._list_hosts import _MAX_NUMBER_OF_HOSTS
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.openapi_monitoring import (
    roles_without_permission,
    site_configurations,
)
from tests.testlib.unit.gui.web_test_app import SetConfig
from tests.testlib.unit.rest_api_client import ClientRegistry

_SITE_ID = "NO_SITE"
_ACTION_MENU_HOST_ROW = {
    "host_name": "heute",
    "host_address": "127.0.0.1",
    "host_filename": "/wato/hosts.mk",
    "host_check_type": 0,
    "host_check_command": "check-mk-host-smart",
    "host_active_checks_enabled": 1,
    "host_pnpgraph_present": 0,
    "host_action_url_expanded": "",
    "host_notes_url_expanded": "",
    "host_custom_variable_names": [],
    "host_custom_variable_values": [],
}

# NOTE: we are a bit contrained on what we can do with the mock livestatus fixture. For instance
# limits and the ``Stats`` meta counts are not faithfully reflected by the mock. Therefore, this
# module mainly tests that the livestatus queries are correctly built based on the user input.


class TestMonitorHostsAuth:
    def test_invalid_credentials(self, clients: ClientRegistry) -> None:
        client = clients.MonitorHosts
        client.set_credentials("foouser", "barpassword")

        resp = client.list_all(limit=100, expect_ok=False)

        assert resp.status_code == HTTPStatus.UNAUTHORIZED
        assert "credentials" in resp.json["detail"]

    def test_normal_user_is_permitted(
        self,
        clients: ClientRegistry,
        with_user: tuple[UserId, str],
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        user_id, _password = with_user
        client = clients.MonitorHosts
        client.set_credentials(*with_user)

        mock_livestatus.add_table("hosts", _HOSTS)
        # Livestatus decides what a user without "see all" may see, so every query names them.
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0", f"AuthUser: {user_id}"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
                f"AuthUser: {user_id}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = client.list_all(limit=_LIMIT)

        assert resp.status_code == HTTPStatus.OK


class TestMonitorHostsQueryParamValidation:
    def test_limit_lower_bound(self, clients: ClientRegistry) -> None:
        resp = clients.MonitorHosts.list_all(limit=-1, expect_ok=False)
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    def test_limit_upper_bound(self, clients: ClientRegistry) -> None:
        resp = clients.MonitorHosts.list_all(limit=1_000_000, expect_ok=False)
        assert resp.status_code == HTTPStatus.BAD_REQUEST

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
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.parametrize(
        "filters",
        [
            pytest.param({}, id="empty payload"),
            pytest.param(
                {"type": "condition", "field": "state", "op": "one_of", "value": []},
                id="min length of 'one_of' condition",
            ),
            pytest.param(
                {"type": "condition", "field": "state", "op": "one_of", "value": ["UP", "UP"]},
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
                    "type": "or",
                    "children": [
                        {"type": "condition", "field": "num_services", "op": "lte", "value": 10},
                    ],
                },
                id="min length of 'or' condition",
            ),
            pytest.param(
                {
                    "type": "condition",
                    "field": "site_id",
                    "op": "one_of",
                    "value": [_SITE_ID, _SITE_ID],
                },
                id="duplicate site ids",
            ),
            pytest.param(
                {
                    "type": "and",
                    "children": [
                        {
                            "type": "condition",
                            "field": "site_id",
                            "op": "one_of",
                            "value": [_SITE_ID],
                        },
                        {
                            "type": "condition",
                            "field": "site_id",
                            "op": "one_of",
                            "value": [_SITE_ID],
                        },
                    ],
                },
                id="a second site_id condition",
            ),
            pytest.param(
                {"type": "condition", "field": "folder", "op": "matches", "value": "^/network"},
                id="folder only supports 'contains'",
            ),
            pytest.param(
                {
                    "type": "or",
                    "children": [
                        {
                            "type": "condition",
                            "field": "site_id",
                            "op": "one_of",
                            "value": [_SITE_ID],
                        },
                        {"type": "condition", "field": "name", "op": "contains", "value": "heute"},
                    ],
                },
                id="site_id nested under 'or'",
            ),
            pytest.param(
                {"type": "condition", "field": "name", "op": "contains", "value": "x\n"},
                id="newline in string value",
            ),
            pytest.param(
                {
                    "type": "condition",
                    "field": "labels",
                    "op": "all_of",
                    "value": ["key:val\nue"],
                },
                id="newline in label choice value",
            ),
        ],
    )
    def test_filters_validation_errors(
        self,
        clients: ClientRegistry,
        filters: dict[str, object],
    ) -> None:
        resp = clients.MonitorHosts.list_all(limit=1000, filters=filters, expect_ok=False)
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.parametrize(
        "filters",
        [
            pytest.param(
                {
                    "type": "condition",
                    "field": "site_id",
                    "op": "one_of",
                    "value": ["no-such-site"],
                },
                id="unknown site id",
            ),
            pytest.param(
                {
                    "type": "and",
                    "children": [
                        {"type": "condition", "field": "name", "op": "contains", "value": "heute"},
                        {
                            "type": "not",
                            "child": {
                                "type": "condition",
                                "field": "site_id",
                                "op": "one_of",
                                "value": ["no-such-site"],
                            },
                        },
                    ],
                },
                id="unknown site id inside the tree",
            ),
        ],
    )
    def test_filters_with_an_unknown_site_are_rejected(
        self,
        clients: ClientRegistry,
        filters: dict[str, object],
    ) -> None:
        resp = clients.MonitorHosts.list_all(limit=1000, filters=filters, expect_ok=False)
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        assert resp.json["detail"] == "Site 'no-such-site' does not exist."


class TestMonitorHosts:
    def test_hosts(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT)

        assert len(resp.json["hosts"]) == len(_HOSTS)

    def test_hosts_without_limit(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
            ]
        )

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
        user_id, _password = with_user
        client = clients.MonitorHosts
        client.set_credentials(*with_user)

        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0", f"AuthUser: {user_id}"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_MAX_NUMBER_OF_HOSTS}",
                f"AuthUser: {user_id}",
            ]
        )

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
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = client.list_all(limit=None)

        assert resp.json["meta"]["limit"] is None


class TestMonitorHostsTableRows:
    def test_per_state_service_counts_match_livestatus_columns(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        # A distinct value per count, so a count read from its neighbour's column is caught.
        counts = {
            "num_services": 21,
            "num_services_ok": 11,
            "num_services_warn": 3,
            "num_services_crit": 4,
            "num_services_unknown": 1,
            "num_services_pending": 2,
        }
        mock_livestatus.add_table("hosts", [_host_row("tally-host", **counts)])
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT)

        [entry] = resp.json["hosts"]
        assert {field: entry[field] for field in counts} == counts

    def test_a_limit_of_zero_returns_no_hosts(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                "Limit: 0",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=0)

        # The mock ignores the Limit header, so an empty list also proves the endpoint's own cut.
        assert resp.json["hosts"] == []


class TestMonitorHostsQuery:
    @pytest.mark.parametrize("query", ["", "   "])
    def test_blank_search_is_treated_as_no_filter(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
        query: str,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT, q=query)

        assert len(resp.json["hosts"]) == len(_HOSTS)

    def test_search_with_no_matches(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "Filter: name ~~ no-such-host",
                "Filter: address ~~ no-such-host",
                "Or: 2",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )
        mock_livestatus.expect_query(
            [
                "GET hosts",
                "Stats: state >= 0",
                "Filter: name ~~ no-such-host",
                "Filter: address ~~ no-such-host",
                "Or: 2",
            ]
        )
        with mock_livestatus():
            resp = clients.MonitorHosts.list_all(limit=_LIMIT, q="no-such-host")

        assert len(resp.json["hosts"]) == 0

    def test_search_only_reads_the_fields_asked_for(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        # The folder is searched by its Setup title; no folder of the test site carries this
        # query, so the search reaches name and alias only.
        search_filter = [
            "Filter: name ~~ no-such-host",
            "Filter: alias ~~ no-such-host",
            "Or: 2",
        ]
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_host_columns('alias', 'folder')}",
                *search_filter,
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0", *search_filter])
        with mock_livestatus():
            resp = clients.MonitorHosts.list_all(
                limit=_LIMIT, q="no-such-host", fields=["alias", "folder"]
            )

        assert len(resp.json["hosts"]) == 0


class TestMonitorHostsFilters:
    def test_filters(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "Filter: num_services <= 10",
                "Filter: state = 0",
                "Filter: has_been_checked = 1",
                "And: 2",
                "Filter: state = 1",
                "Filter: has_been_checked = 1",
                "And: 2",
                "Or: 2",
                "And: 2",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )
        mock_livestatus.expect_query(
            [
                "GET hosts",
                "Stats: state >= 0",
                "Filter: num_services <= 10",
                "Filter: state = 0",
                "Filter: has_been_checked = 1",
                "And: 2",
                "Filter: state = 1",
                "Filter: has_been_checked = 1",
                "And: 2",
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
                "is_flapping": False,
                "stale": False,
                "legacy_host_status_link": "view.py?view_name=hoststatus&site=NO_SITE&host=heute",
            },
        ]

    def test_never_checked_host_is_reported_as_pending(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table(
            "hosts",
            [{**_HOSTS[0], "name": "pending-host", "has_been_checked": 0}],
        )
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT)

        assert resp.json["hosts"][0]["state"] == "PENDING"

    def test_host_with_recorded_time_series_links_to_its_graphs(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", [{**_HOSTS[0], "pnpgraph_present": 1}])
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_host_columns('graphs_link')}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT, fields=["graphs_link"])

        assert resp.json["hosts"][0]["graphs_link"] == (
            "view.py?view_name=host_graphs&site=NO_SITE&host=heute"
        )

    def test_hosts_filtered_by_folder(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        # A folder is filtered by the title Setup shows for it, which Livestatus knows nothing
        # about: the folders carrying the value are resolved here and asked for by file. The test
        # site has the root folder only, whose fallback title is "Main".
        folder_lines = ["Filter: filename = /wato/hosts.mk"]
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                *folder_lines,
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0", *folder_lines])
        filters = {"type": "condition", "field": "folder", "op": "contains", "value": "Main"}
        with mock_livestatus():
            clients.MonitorHosts.list_all(limit=_LIMIT, filters=filters)

    def test_hosts_filtered_by_a_folder_name_that_is_no_title(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        # The folder's path used to be filterable and is not any more. No title carries it, so no
        # host does - said out loud, since sending no filter at all would select every host. That
        # the query selects nothing is covered by tests/unit/cmk/gui/monitor/hosts/test_folder.py:
        # the mock evaluates no `Negate:`, so it cannot answer that here.
        folder_lines = ["Filter: state >= 0", "Negate:"]
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                *folder_lines,
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0", *folder_lines])
        filters = {"type": "condition", "field": "folder", "op": "contains", "value": "/network"}
        with mock_livestatus():
            clients.MonitorHosts.list_all(limit=_LIMIT, filters=filters)

    def test_hosts_filtered_by_site(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        # The grand total stays unscoped (queried on every configured site, per the default
        # `expect_query` routing), unlike the fetch/matched-count queries below.
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ],
            sites=[_SITE_ID],
        )
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"], sites=[_SITE_ID])
        filters = {"type": "condition", "field": "site_id", "op": "one_of", "value": [_SITE_ID]}

        with mock_livestatus():
            resp = clients.MonitorHosts.list_all(limit=_LIMIT, filters=filters)

        assert len(resp.json["hosts"]) == len(_HOSTS)
        assert resp.json["meta"]["matched"] == len(_HOSTS)
        assert resp.json["meta"]["total"] == len(_HOSTS)

    def test_hosts_excluding_a_site(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
        set_config: SetConfig,
    ) -> None:
        # "remote" needs to be a real configured site (not just a mock-livestatus fake site) for
        # the handler to accept it, and for the complement (every site except "remote") to be
        # computed against the right set of configured sites.
        with set_config(sites=site_configurations([_SITE_ID, "remote", "local"])):
            mock_livestatus.add_table("hosts", _HOSTS)
            mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
            # Excluding "remote" restricts the fetch/matched-count queries to the two remaining
            # configured sites (NO_SITE, local) rather than broadcasting to all three.
            mock_livestatus.expect_query(
                [
                    "GET hosts",
                    f"Columns: {_HOST_TABLE_COLUMNS}",
                    "OrderBy: name asc natural",
                    f"Limit: {_LIMIT}",
                ],
                sites=[_SITE_ID, "local"],
            )
            mock_livestatus.expect_query(
                ["GET hosts", "Stats: state >= 0"], sites=[_SITE_ID, "local"]
            )
            filters = {
                "type": "not",
                "child": {
                    "type": "condition",
                    "field": "site_id",
                    "op": "one_of",
                    "value": ["remote"],
                },
            }

            with mock_livestatus():
                resp = clients.MonitorHosts.list_all(limit=_LIMIT, filters=filters)

        assert len(resp.json["hosts"]) == len(_HOSTS)
        assert resp.json["meta"]["matched"] == len(_HOSTS)
        assert resp.json["meta"]["total"] == len(_HOSTS)

    def test_hosts_excluding_every_site(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
        set_config: SetConfig,
    ) -> None:
        # Negating every currently configured site computes an empty site scope. Livestatus's
        # `only_sites([])` can't express "zero sites" -- an empty list is falsy to it and it falls
        # back to "no restriction" instead -- so this must be short-circuited before ever building
        # a fetch/matched-count query, rather than silently returning every host from every site.
        with set_config(sites=site_configurations([_SITE_ID])):
            mock_livestatus.add_table("hosts", _HOSTS)
            mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
            filters = {
                "type": "not",
                "child": {
                    "type": "condition",
                    "field": "site_id",
                    "op": "one_of",
                    "value": [_SITE_ID],
                },
            }

            with mock_livestatus():
                resp = clients.MonitorHosts.list_all(limit=_LIMIT, filters=filters)

        assert resp.json["hosts"] == []
        assert resp.json["meta"]["matched"] == 0
        assert resp.json["meta"]["total"] == len(_HOSTS)


class TestMonitorHostsFields:
    def test_non_default_field_omitted(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

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
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_host_columns(_NON_DEFAULT_FIELD)}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

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
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_host_columns(*_OPTIONAL_FIELDS_UNDER_TEST)}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        optional_fields = list(_OPTIONAL_FIELDS_UNDER_TEST)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT, fields=optional_fields)

        host = next(h for h in resp.json["hosts"] if h["name"] == "heute")

        assert all(field in host for field in optional_fields)

    def test_sort_column_is_read_even_when_the_response_omits_it(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        """Sorting happens in Python, so a sort column has to be read even if no field wants it."""
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_host_columns(*_DEFAULT_FIELDS, _NON_DEFAULT_FIELD)}",
                "OrderBy: alias asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT, sort=[f"{_NON_DEFAULT_FIELD}:asc"])

        by_alias = sorted(_HOSTS, key=lambda host: str(host["alias"]).lower())
        assert [host["name"] for host in resp.json["hosts"]] == [host["name"] for host in by_alias]
        assert _NON_DEFAULT_FIELD not in resp.json["hosts"][0]

    def test_labels_are_read_and_returned_only_when_requested(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_host_columns('labels')}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT, fields=["labels"])

        host = next(h for h in resp.json["hosts"] if h["name"] == "heute")
        assert host["labels"] == {"cmk/site": {"value": "heute", "source": "discovered"}}

    def test_labels_are_omitted_unless_requested(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT)

        assert "labels" not in resp.json["hosts"][0]

    def test_tags_are_read_and_returned_only_when_requested(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_host_columns('tags')}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT, fields=["tags"])

        host = next(h for h in resp.json["hosts"] if h["name"] == "heute")
        assert host["tags"] == {"criticality": "prod"}

    def test_tags_are_omitted_unless_requested(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT)

        assert "tags" not in resp.json["hosts"][0]

    def test_contacts_are_read_and_returned_only_when_requested(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_host_columns('contacts')}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT, fields=["contacts"])

        host = next(h for h in resp.json["hosts"] if h["name"] == "heute")
        assert host["contacts"] == ["hh"]

    def test_contacts_are_omitted_unless_requested(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT)

        assert "contacts" not in resp.json["hosts"][0]

    def test_contact_groups_are_read_and_returned_only_when_requested(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_host_columns('contact_groups')}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT, fields=["contact_groups"])

        host = next(h for h in resp.json["hosts"] if h["name"] == "heute")
        assert host["contact_groups"] == ["all"]

    def test_contact_groups_are_omitted_unless_requested(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT)

        assert "contact_groups" not in resp.json["hosts"][0]

    def test_num_relations_counts_only_the_relations_that_reach_the_reader(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS_WITH_RELATIONS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        # Asked once for the whole listing, before the sites are narrowed, so the count does not
        # change with the reader's site filter.
        mock_livestatus.expect_query(
            [
                "GET hosts",
                "Columns: name",
                "Filter: custom_variable_names >= CMK_RELATIONS",
            ]
        )
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_host_columns('num_relations')}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT, fields=["num_relations"])

        # "heute" is related to "gestern" and to "gone"; only the former is a host any site knows,
        # so the number promises exactly the cards the host details will show.
        assert {host["name"]: host["num_relations"] for host in resp.json["hosts"]} == {
            "heute": 1,
            "gestern": 1,
            "morgen": 0,
        }

    def test_num_relations_is_omitted_unless_requested(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS_WITH_RELATIONS)
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        # No pre-query either: a listing without the count needs none of the counterparts.
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT)

        assert "num_relations" not in resp.json["hosts"][0]


class TestMonitorHostsSort:
    def test_default_sort_merges_and_orders_across_sites(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        # Neither site hands its rows back in order. The merged rows have to interleave into one
        # natural name order: not per site, and not lexical (host10 after host2).
        _connect_two_sites(mock_livestatus)
        mock_livestatus.add_table("hosts", [_host_row("host10"), _host_row("host2")], site="site_a")
        mock_livestatus.add_table("hosts", [_host_row("host1"), _host_row("host20")], site="site_b")
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"])
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ]
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_all(limit=_LIMIT)

        # Each row keeps the site that answered it, which the actions address the host by.
        assert [(host["name"], host["site_id"]) for host in resp.json["hosts"]] == [
            ("host1", "site_b"),
            ("host2", "site_a"),
            ("host10", "site_a"),
            ("host20", "site_b"),
        ]


class TestMonitorHostOverviewAuth:
    def test_invalid_credentials(self, clients: ClientRegistry) -> None:
        client = clients.MonitorHosts
        client.set_credentials("foouser", "barpassword")

        resp = client.get(hostname="heute", site_id=_SITE_ID, expect_ok=False)

        assert resp.status_code == HTTPStatus.UNAUTHORIZED
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

        assert resp.status_code == HTTPStatus.NOT_FOUND


class TestMonitorHostOverviewQueryParamValidation:
    def test_unknown_site_is_rejected(self, clients: ClientRegistry) -> None:
        resp = clients.MonitorHosts.get(hostname="heute", site_id="no-such-site", expect_ok=False)
        assert resp.status_code == HTTPStatus.BAD_REQUEST


class TestMonitorHostActionMenuAuth:
    def test_invalid_credentials(self, clients: ClientRegistry) -> None:
        client = clients.MonitorHosts
        client.set_credentials("foouser", "barpassword")

        resp = client.action_menu(hostname="heute", site_id=_SITE_ID, expect_ok=False)

        assert resp.status_code == HTTPStatus.UNAUTHORIZED
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

        assert resp.status_code == HTTPStatus.NOT_FOUND


class TestMonitorHostActionMenuQueryParamValidation:
    def test_unknown_site_is_rejected(self, clients: ClientRegistry) -> None:
        resp = clients.MonitorHosts.action_menu(
            hostname="heute", site_id="no-such-site", expect_ok=False
        )
        assert resp.status_code == HTTPStatus.BAD_REQUEST


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

        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_existing_host_lists_its_actions(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", [_ACTION_MENU_HOST_ROW])
        mock_livestatus.expect_query(
            ["GET hosts", "Filter: host_name = heute"],
            match_type="loose",
            sites=[_SITE_ID],
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.action_menu(
                hostname="heute", site_id=_SITE_ID, expect_ok=False
            )

        assert resp.status_code == HTTPStatus.OK
        assert resp.json["items"]

    def test_normal_user_sees_the_actions_of_an_existing_host(
        self,
        clients: ClientRegistry,
        with_user: tuple[UserId, str],
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        client = clients.MonitorHosts
        client.set_credentials(*with_user)
        mock_livestatus.add_table("hosts", [_ACTION_MENU_HOST_ROW])
        mock_livestatus.expect_query(
            ["GET hosts", "Filter: host_name = heute"],
            match_type="loose",
            sites=[_SITE_ID],
        )

        with mock_livestatus(expect_status_query=True):
            resp = client.action_menu(hostname="heute", site_id=_SITE_ID, expect_ok=False)

        assert resp.status_code == HTTPStatus.OK
        assert resp.json["items"]


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
                    **_OVERVIEW_HOST,
                    "last_check": time.time() - 30,
                    "last_state_change": time.time(),
                    "tags": {"criticality": "prod"},
                    "labels": {"cmk/os_family": "linux"},
                    "label_sources": {"cmk/os_family": "discovered"},
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
            "is_flapping": False,
            "stale": False,
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
            "last_check": 1783942710,
            "last_state_change": 1783942740,
            "customer": None,
            "folder": "",
            "contact_groups": ["all"],
            "tags": {"criticality": "prod"},
            "labels": {"cmk/os_family": {"value": "linux", "source": "discovered"}},
            "legacy_host_status_link": "view.py?view_name=hoststatus&site=NO_SITE&host=heute",
            "setup_access": False,
            "relations": [],
            "more_relations": False,
        }

    @time_machine.travel("2026-07-13 11:39:00+00:00", tick=False)
    def test_get_host_overview_reads_the_state_of_every_related_host(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table(
            "hosts",
            [
                {
                    **_OVERVIEW_HOST,
                    "custom_variables": {
                        "CMK_RELATIONS": json.dumps(
                            [
                                # The card names the end the related host sits at in return.
                                {
                                    "kind": "management",
                                    "direction": "child",
                                    "host": "mgmt-heute",
                                    "site": _SITE_ID,
                                },
                                {
                                    "kind": "management",
                                    "direction": "child",
                                    "host": "gone",
                                    "site": _SITE_ID,
                                },
                            ]
                        )
                    },
                    "custom_variable_names": ["CMK_RELATIONS"],
                },
                {
                    **_OVERVIEW_HOST,
                    "name": "mgmt-heute",
                    "state": 1,
                    "num_services": 4,
                    "num_services_ok": 3,
                    "num_services_crit": 1,
                    "last_check": 1783942680,
                    "custom_variables": {
                        "CMK_RELATIONS": json.dumps(
                            [
                                {
                                    "kind": "management",
                                    "direction": "parent",
                                    "host": "heute",
                                    "site": _SITE_ID,
                                }
                            ]
                        )
                    },
                    "custom_variable_names": ["CMK_RELATIONS"],
                },
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
        # The same set the relation count reads, so the hidden hosts are left out before the cut.
        mock_livestatus.expect_query(
            [
                "GET hosts",
                "Columns: name",
                "Filter: custom_variable_names >= CMK_RELATIONS",
            ]
        )
        mock_livestatus.expect_query(
            [
                "GET hosts",
                (
                    "Columns: name state has_been_checked num_services num_services_ok "
                    "num_services_warn num_services_crit num_services_unknown "
                    "num_services_pending"
                ),
                "Filter: name = mgmt-heute",
                # Both ends carry the macro, so a host that does not is not the counterpart.
                "Filter: custom_variable_names >= CMK_RELATIONS",
                "And: 2",
            ],
            # The export resolved where the related hosts live, so only their site is asked.
            sites=[_SITE_ID],
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get(hostname="heute", site_id=_SITE_ID)

        # The relation to "gone" names a host no site knows, so no card is built for it.
        assert resp.json["relations"] == [
            {
                "host_name": "mgmt-heute",
                "kind": "management",
                "direction": "parent",
                # Worded by the server, so the frontend keeps no label map of its own.
                "relation_type": "Management board",
                "site_id": "NO_SITE",
                "health": {
                    "state": "DOWN",
                    "service_counts": {
                        "total": 4,
                        "ok": 3,
                        "warn": 0,
                        "crit": 1,
                        "unknown": 0,
                        "pending": 0,
                    },
                },
            }
        ]

    @time_machine.travel("2026-07-13 11:39:00+00:00", tick=False)
    def test_get_host_overview_without_multi_tenancy_has_no_customer(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("hosts", [_OVERVIEW_HOST])
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

        assert resp.status_code == HTTPStatus.NOT_FOUND


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

    def test_reschedule_sends_each_command_to_the_site_named_for_its_host(
        self,
        clients: ClientRegistry,
        set_config: SetConfig,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        # The mock keeps one expectation queue per site, so a command sent to the wrong site
        # finds nothing waiting for it there and fails the test.
        mock_livestatus.expect_query(
            "COMMAND [...] SCHEDULE_FORCED_HOST_CHECK;heute;...",
            match_type="ellipsis",
            sites=[_SITE_ID],
        )
        mock_livestatus.expect_query(
            "COMMAND [...] SCHEDULE_FORCED_HOST_CHECK;gestern;...",
            match_type="ellipsis",
            sites=["remote"],
        )

        with (
            set_config(sites=site_configurations([_SITE_ID, "remote", "local"])),
            mock_livestatus(expect_status_query=True),
        ):
            resp = clients.MonitorHosts.reschedule(
                hosts=[
                    {"site_id": _SITE_ID, "name": "heute"},
                    {"site_id": "remote", "name": "gestern"},
                ]
            )

        assert resp.json["rescheduled"] == 2

    @pytest.mark.parametrize(
        "denied_permission, expected_reason",
        [
            pytest.param("action.reschedule", "Reschedule checks", id="the reschedule permission"),
            pytest.param(
                "general.act",
                "Perform commands in views",
                id="the general permission to act on monitored objects",
            ),
        ],
    )
    def test_reschedule_is_refused_without_a_required_permission(
        self,
        clients: ClientRegistry,
        with_user: tuple[UserId, str],
        load_config: Config,
        set_config: SetConfig,
        mock_livestatus: MockLiveStatusConnection,
        denied_permission: str,
        expected_reason: str,
    ) -> None:
        # The page only hides an action the user may not perform; the endpoint refuses it too,
        # and no command reaches the core (none is expected).
        clients.MonitorHosts.set_credentials(*with_user)
        roles = roles_without_permission(load_config, "user", denied_permission)

        with set_config(roles=roles), mock_livestatus(expect_status_query=False):
            resp = clients.MonitorHosts.reschedule(
                hosts=[{"site_id": _SITE_ID, "name": "heute"}], expect_ok=False
            )

        assert resp.status_code == HTTPStatus.FORBIDDEN
        assert expected_reason in resp.json["detail"]


_LIMIT = 1000
_NON_DEFAULT_FIELD = "alias"
_OPTIONAL_FIELDS_UNDER_TEST = ("alias", "folder", "last_check", "last_state_change")
_HOSTS = [
    {
        "name": "heute",
        "address": "127.0.0.1",
        "alias": "Today",
        "state": 0,
        "has_been_checked": 1,
        "num_services": 10,
        "num_services_ok": 10,
        "num_services_warn": 0,
        "num_services_crit": 0,
        "num_services_unknown": 0,
        "num_services_pending": 0,
        "acknowledged": 0,
        "scheduled_downtime_depth": 0,
        "notifications_enabled": 1,
        "comments": [],
        "modified_attributes_list": [],
        "active_checks_enabled": 1,
        "accept_passive_checks": 1,
        "in_notification_period": 1,
        "in_service_period": 1,
        "in_check_period": 1,
        "is_flapping": 0,
        "staleness": 0.0,
        "pnpgraph_present": 0,
        "last_check": 1700000000,
        "last_state_change": 1700000060,
        "filename": "/wato/hosts.mk",
        "labels": {"cmk/site": "heute"},
        "label_sources": {"cmk/site": "discovered"},
        "tags": {"criticality": "prod"},
        "contacts": ["hh"],
        "contact_groups": ["all"],
        "custom_variables": {},
    },
    {
        "name": "gestern",
        "address": "127.0.10.1",
        "alias": "Yesterday",
        "state": 1,
        "has_been_checked": 1,
        "num_services": 20,
        "num_services_ok": 20,
        "num_services_warn": 0,
        "num_services_crit": 0,
        "num_services_unknown": 0,
        "num_services_pending": 0,
        "acknowledged": 0,
        "scheduled_downtime_depth": 0,
        "notifications_enabled": 1,
        "comments": [],
        "modified_attributes_list": [],
        "active_checks_enabled": 1,
        "accept_passive_checks": 1,
        "in_notification_period": 1,
        "in_service_period": 1,
        "in_check_period": 1,
        "is_flapping": 0,
        "staleness": 0.0,
        "pnpgraph_present": 0,
        "last_check": 1700000100,
        "last_state_change": 1700000160,
        "filename": "/wato/network/hosts.mk",
        "labels": {"cmk/site": "gestern"},
        "label_sources": {"cmk/site": "discovered"},
        "tags": {"criticality": "prod"},
        "contacts": ["hh"],
        "contact_groups": ["all"],
        "custom_variables": {},
    },
    {
        "name": "morgen",
        "address": "127.0.2.1",
        "alias": "Tomorrow",
        "state": 2,
        "has_been_checked": 1,
        "num_services": 30,
        "num_services_ok": 30,
        "num_services_warn": 0,
        "num_services_crit": 0,
        "num_services_unknown": 0,
        "num_services_pending": 0,
        "acknowledged": 0,
        "scheduled_downtime_depth": 0,
        "notifications_enabled": 1,
        "comments": [],
        "modified_attributes_list": [],
        "active_checks_enabled": 1,
        "accept_passive_checks": 1,
        "in_notification_period": 1,
        "in_service_period": 1,
        "in_check_period": 1,
        "is_flapping": 0,
        "staleness": 0.0,
        "pnpgraph_present": 0,
        "last_check": 1700000200,
        "last_state_change": 1700000260,
        # Not managed via Setup, e.g. added directly to the monitoring core.
        "filename": "/omd/sites/heute/etc/nagios/conf.d/hosts.mk",
        "labels": {"cmk/site": "morgen"},
        "label_sources": {"cmk/site": "discovered"},
        "tags": {"criticality": "prod"},
        "contacts": ["hh"],
        "contact_groups": ["all"],
        "custom_variables": {},
    },
]
# Both ends of an exported relation carry the macro, so a counterpart carries it in return. Here
# "heute" and "gestern" are related to each other, and "heute" additionally names a host no site
# knows.
_HOSTS_WITH_RELATIONS = [
    {
        **_HOSTS[0],
        "custom_variables": {
            "CMK_RELATIONS": json.dumps(
                [
                    {
                        "kind": "management",
                        "direction": "child",
                        "host": "gestern",
                        "site": _SITE_ID,
                    },
                    {"kind": "management", "direction": "child", "host": "gone", "site": _SITE_ID},
                ]
            )
        },
        "custom_variable_names": ["CMK_RELATIONS"],
    },
    {
        **_HOSTS[1],
        "custom_variables": {
            "CMK_RELATIONS": json.dumps(
                [{"kind": "management", "direction": "parent", "host": "heute", "site": _SITE_ID}]
            )
        },
        "custom_variable_names": ["CMK_RELATIONS"],
    },
    {**_HOSTS[2], "custom_variable_names": []},
]
# Columns every host row needs, followed by the ones a request has to ask for. Both lists are in
# the order the query names them, so the expectations below read like the real `Columns:` header.
_MANDATORY_COLUMNS = (
    "name",
    "state",
    "has_been_checked",
    "acknowledged",
    "scheduled_downtime_depth",
    "notifications_enabled",
    "comments",
    "modified_attributes_list",
    "active_checks_enabled",
    "accept_passive_checks",
    "in_notification_period",
    "in_service_period",
    "in_check_period",
    "is_flapping",
    "staleness",
)
_OPTIONAL_COLUMNS = {
    "alias": "alias",
    "address": "address",
    "num_services": "num_services",
    "num_services_ok": "num_services_ok",
    "num_services_warn": "num_services_warn",
    "num_services_crit": "num_services_crit",
    "num_services_unknown": "num_services_unknown",
    "num_services_pending": "num_services_pending",
    "num_relations": "custom_variables",
    "folder": "filename",
    "last_check": "last_check",
    "last_state_change": "last_state_change",
    "labels": "labels label_sources",
    "tags": "tags",
    "contacts": "contacts",
    "contact_groups": "contact_groups",
    "graphs_link": "pnpgraph_present",
}
_DEFAULT_FIELDS = (
    "address",
    "num_services",
    "num_services_ok",
    "num_services_warn",
    "num_services_crit",
    "num_services_unknown",
    "num_services_pending",
)


def _host_row(name: str, **overrides: object) -> dict[str, object]:
    """A complete host row, so a column the endpoint starts to read needs no edit here."""
    return {**_HOSTS[0], "name": name, "alias": name.title(), **overrides}


def _connect_two_sites(mock_livestatus: MockLiveStatusConnection) -> None:
    mock_livestatus.set_sites(["site_a", "site_b"])
    # Each site answers the connection probe with this row. The mock's default row pairs the
    # legacy edition name with today's version, and the site check drops such a site.
    for site_id in mock_livestatus.sites:
        mock_livestatus.add_table("status", [_STATUS_ROW], site=site_id)


def _host_columns(*fields: str) -> str:
    """The `Columns:` a request asking for `fields` reads (defaults when none are named)."""
    wanted = set(fields) if fields else set(_DEFAULT_FIELDS)
    return " ".join(
        [
            *_MANDATORY_COLUMNS,
            *(column for field, column in _OPTIONAL_COLUMNS.items() if field in wanted),
        ]
    )


_HOST_TABLE_COLUMNS = _host_columns()
_STATUS_ROW = {
    "livestatus_version": "1.0.0",
    "program_version": "Check_MK 1.0.0",
    "program_start": 0,
    "num_hosts": 1,
    "num_services": 1,
    "max_long_output_size": 2000,
    "core_pid": 12345,
    "edition": "community",
}
_OVERVIEW_HOST: dict[str, object] = {
    "name": "heute",
    "alias": "Today",
    "address": "127.0.0.1",
    "state": 0,
    "has_been_checked": 1,
    "num_services": 10,
    "num_services_ok": 10,
    "num_services_warn": 0,
    "num_services_crit": 0,
    "num_services_unknown": 0,
    "num_services_pending": 0,
    "acknowledged": 0,
    "scheduled_downtime_depth": 0,
    "notifications_enabled": 1,
    "comments": [],
    "modified_attributes_list": [],
    "active_checks_enabled": 1,
    "accept_passive_checks": 1,
    "in_notification_period": 1,
    "in_service_period": 1,
    "in_check_period": 1,
    "is_flapping": 0,
    "staleness": 0.0,
    "last_check": 0,
    "last_state_change": 0,
    "contact_groups": [],
    "tags": {},
    "labels": {},
    "label_sources": {},
    "filename": "",
    "custom_variables": {},
}

_HOST_OVERVIEW_COLUMNS = "name alias address state has_been_checked num_services num_services_ok num_services_warn num_services_crit num_services_unknown num_services_pending acknowledged scheduled_downtime_depth notifications_enabled comments modified_attributes_list active_checks_enabled accept_passive_checks in_notification_period in_service_period in_check_period is_flapping staleness last_check last_state_change contact_groups tags labels label_sources filename custom_variables"

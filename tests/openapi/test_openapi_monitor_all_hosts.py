#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest
import time_machine

from livestatus import SiteConfiguration

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.monitor.hosts._api._list_hosts import _MAX_NUMBER_OF_HOSTS
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.gui.web_test_app import SetConfig
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
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"], match_type="loose")
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_LIMIT}",
            ],
            match_type="loose",
        )

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
        client = clients.MonitorHosts
        client.set_credentials(*with_user)

        mock_livestatus.add_table("hosts", _HOSTS)
        # see_all-less user → sites.live() adds an AuthUser line; match loosely to tolerate it.
        mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"], match_type="loose")
        mock_livestatus.expect_query(
            [
                "GET hosts",
                f"Columns: {_HOST_TABLE_COLUMNS}",
                "OrderBy: name asc natural",
                f"Limit: {_MAX_NUMBER_OF_HOSTS}",
            ],
            match_type="loose",
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
                "Filter: state = 1",
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
        # `SiteIdConverter.should_exist` to accept it, and for the complement (every site except
        # "remote") to be computed against the right set of configured sites.
        with set_config(sites=_site_configs([SiteId(_SITE_ID), SiteId("remote"), SiteId("local")])):
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
        with set_config(sites=_site_configs([SiteId(_SITE_ID)])):
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
                f"Columns: {_host_columns('labels')} labels label_sources",
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
            "last_check": 1783942710,
            "last_state_change": 1783942740,
            "customer": None,
            "folder": "",
            "contact_groups": ["all"],
            "tags": {"criticality": "prod"},
            "labels": {"cmk/os_family": {"value": "linux", "source": "discovered"}},
            "legacy_host_status_link": "view.py?view_name=hoststatus&site=NO_SITE&host=heute",
        }

    @time_machine.travel("2026-07-13 11:39:00+00:00", tick=False)
    def test_get_host_overview_without_multi_tenancy_has_no_customer(
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


def _site_configs(site_ids: list[SiteId]) -> dict[SiteId, SiteConfiguration]:
    return {
        site_id: SiteConfiguration(
            id=site_id,
            alias=str(site_id),
            socket=("local", None),
            disable_wato=True,
            disabled=False,
            insecure=False,
            url_prefix=f"/{site_id}/",
            multisiteurl="",
            persist=False,
            replicate_ec=False,
            replicate_mkps=False,
            replication=None,
            timeout=5,
            user_login=True,
            proxy=None,
            user_attribute_sync_connections="all",
            status_host=None,
            message_broker_port=5672,
            is_trusted=False,
        )
        for site_id in site_ids
    }


_LIMIT = 1000
_NON_DEFAULT_FIELD = "alias"
_OPTIONAL_FIELDS_UNDER_TEST = ("alias", "folder", "last_check", "last_state_change")
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
        "labels": {"cmk/site": "heute"},
        "label_sources": {"cmk/site": "discovered"},
        "tags": {"criticality": "prod"},
        "contacts": ["hh"],
        "contact_groups": ["all"],
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
        "labels": {"cmk/site": "gestern"},
        "label_sources": {"cmk/site": "discovered"},
        "tags": {"criticality": "prod"},
        "contacts": ["hh"],
        "contact_groups": ["all"],
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
        "labels": {"cmk/site": "morgen"},
        "label_sources": {"cmk/site": "discovered"},
        "tags": {"criticality": "prod"},
        "contacts": ["hh"],
        "contact_groups": ["all"],
    },
]
# Columns every host row needs, followed by the ones a request has to ask for. Both lists are in
# the order the query names them, so the expectations below read like the real `Columns:` header.
_MANDATORY_COLUMNS = ("name", "state", "acknowledged", "scheduled_downtime_depth")
_OPTIONAL_COLUMNS = {
    "alias": "alias",
    "address": "address",
    "num_services": "num_services",
    "num_services_ok": "num_services_ok",
    "num_services_warn": "num_services_warn",
    "num_services_crit": "num_services_crit",
    "num_services_unknown": "num_services_unknown",
    "num_services_pending": "num_services_pending",
    "folder": "filename",
    "last_check": "last_check",
    "last_state_change": "last_state_change",
    "tags": "tags",
    "contacts": "contacts",
    "contact_groups": "contact_groups",
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
_HOST_OVERVIEW_COLUMNS = "name alias address state num_services num_services_ok num_services_warn num_services_crit num_services_unknown num_services_pending acknowledged scheduled_downtime_depth last_check last_state_change contact_groups tags labels label_sources filename"

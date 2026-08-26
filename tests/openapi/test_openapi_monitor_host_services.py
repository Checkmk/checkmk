#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Iterator

import pytest
import time_machine

from cmk.ccc.user import UserId
from cmk.graphing.v1 import metrics, perfometers, Title
from cmk.gui.graphing import metrics_from_api, perfometers_from_api
from cmk.gui.graphing._from_api import parse_metric_from_api
from cmk.gui.monitor.services._api._list_host_services import _MAX_HOST_SVC_LIMIT
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.rest_api_client import ClientRegistry


@pytest.fixture(name="registered_perfometer")
def fixture_registered_perfometer() -> Iterator[None]:
    metrics_from_api.register(
        parse_metric_from_api(
            metrics.Metric(
                name="test_metric",
                title=Title("Test metric"),
                unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(0)),
                color=metrics.Color.BLUE,
            )
        )
    )
    perfometers_from_api.register(
        perfometers.Perfometer(
            name="test_perfometer",
            focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
            segments=["test_metric"],
        )
    )
    try:
        yield
    finally:
        metrics_from_api.unregister("test_metric")
        perfometers_from_api.unregister("test_perfometer")


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

    @pytest.mark.parametrize(
        "sort",
        [
            pytest.param(["nameasc"], id="missing colon separator"),
            pytest.param(["invalid:asc"], id="invalid column"),
            pytest.param(["name:invalid"], id="invalid direction"),
            pytest.param(["address:asc"], id="host-only column"),
            pytest.param(["name:asc", "name:desc"], id="duplicated column"),
        ],
    )
    def test_invalid_sort_params(self, clients: ClientRegistry, sort: list[str]) -> None:
        resp = clients.MonitorHosts.list_host_services(
            hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT, sort=sort, expect_ok=False
        )
        assert resp.status_code == 400

    @pytest.mark.parametrize(
        "filters",
        [
            pytest.param({}, id="empty payload"),
            pytest.param(
                {"type": "condition", "field": "state", "op": "one_of", "value": []},
                id="min length of 'one_of' condition",
            ),
            pytest.param(
                {"type": "condition", "field": "state", "op": "one_of", "value": ["OK", "OK"]},
                id="uniqueness in 'one_of' condition",
            ),
            pytest.param(
                {"type": "condition", "field": "name", "op": "contains", "value": "x\n"},
                id="newline in string value",
            ),
            pytest.param(
                {
                    "type": "and",
                    "children": [
                        {"type": "condition", "field": "state", "op": "one_of", "value": ["OK"]},
                    ],
                },
                id="min length of 'and' condition",
            ),
        ],
    )
    def test_filters_validation_errors(
        self,
        clients: ClientRegistry,
        filters: dict[str, object],
    ) -> None:
        resp = clients.MonitorHosts.list_host_services(
            hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT, filters=filters, expect_ok=False
        )
        assert resp.status_code == 400


class TestMonitorHostServicesFilters:
    @time_machine.travel("2026-07-13 11:39:00+00:00", tick=False)
    def test_single_filter(
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
                    "perf_data": "",
                    "labels": {},
                    "label_sources": {},
                    "tags": {},
                    "check_command": "check_mk-test",
                    "host_name": _HOSTNAME,
                    "state": 1,
                    "plugin_output": "WARN - load average: 3.10, 2.05, 1.01",
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
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
                "Filter: state = 1",
                "Filter: state = 2",
                "Or: 2",
                _DEFAULT_ORDER_BY,
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
        mock_livestatus.expect_query(
            [
                "GET services",
                "Stats: state >= 0",
                f"Filter: host_name = {_HOSTNAME}",
                "Filter: state = 1",
                "Filter: state = 2",
                "Or: 2",
            ],
            sites=[_SITE_ID],
        )
        filters = {
            "type": "condition",
            "field": "state",
            "op": "one_of",
            "value": ["WARN", "CRIT"],
        }

        with mock_livestatus():
            resp = clients.MonitorHosts.list_host_services(
                hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT, filters=filters
            )

        assert resp.json["services"] == [
            {
                "name": "CPU load",
                "state": "WARN",
                "is_flapping": False,
                "stale": False,
                "summary": "WARN - load average: 3.10, 2.05, 1.01",
                "last_check": 1783942740,
                "last_state_change": 1783942740,
            }
        ]

    @time_machine.travel("2026-07-13 11:39:00+00:00", tick=False)
    def test_with_multiple_conditions(
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
                    "perf_data": "",
                    "labels": {},
                    "label_sources": {},
                    "tags": {},
                    "check_command": "check_mk-test",
                    "host_name": _HOSTNAME,
                    "state": 1,
                    "plugin_output": "WARN - load average: 3.10, 2.05, 1.01",
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
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
                "Filter: description ~~ CPU",
                "Filter: state = 1",
                "And: 2",
                _DEFAULT_ORDER_BY,
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
        mock_livestatus.expect_query(
            [
                "GET services",
                "Stats: state >= 0",
                f"Filter: host_name = {_HOSTNAME}",
                "Filter: description ~~ CPU",
                "Filter: state = 1",
                "And: 2",
            ],
            sites=[_SITE_ID],
        )
        filters = {
            "type": "and",
            "children": [
                {"type": "condition", "field": "name", "op": "contains", "value": "CPU"},
                {"type": "condition", "field": "state", "op": "one_of", "value": ["WARN"]},
            ],
        }

        with mock_livestatus():
            resp = clients.MonitorHosts.list_host_services(
                hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT, filters=filters
            )

        assert resp.json["services"] == [
            {
                "name": "CPU load",
                "state": "WARN",
                "is_flapping": False,
                "stale": False,
                "summary": "WARN - load average: 3.10, 2.05, 1.01",
                "last_check": 1783942740,
                "last_state_change": 1783942740,
            }
        ]


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
                    "perf_data": "",
                    "labels": {},
                    "label_sources": {},
                    "tags": {},
                    "check_command": "check_mk-test",
                    "host_name": _HOSTNAME,
                    "state": 0,
                    "plugin_output": "OK - load average: 0.10, 0.05, 0.01",
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
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
                _DEFAULT_ORDER_BY,
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
                    "is_flapping": False,
                    "stale": False,
                    "summary": "OK - load average: 0.10, 0.05, 0.01",
                    "last_check": 1783942710,
                    "last_state_change": 1783942740,
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

    def test_service_labels_are_returned_with_their_source(
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
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
                    "last_check": time.time() - 30,
                    "last_state_change": time.time(),
                    "perf_data": "",
                    "check_command": "check_mk-test",
                    "labels": {"cmk/check_plugin": "cpu_load", "owner": "platform"},
                    "label_sources": {"cmk/check_plugin": "discovered", "owner": "explicit"},
                    "tags": {},
                }
            ],
        )
        _expect_list_services_queries(mock_livestatus, extra_columns="labels label_sources")

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_host_services(
                hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT, fields=["labels"]
            )

        assert resp.json["services"][0]["labels"] == {
            "cmk/check_plugin": {"value": "cpu_load", "source": "discovered"},
            "owner": {"value": "platform", "source": "explicit"},
        }

    def test_service_tags_are_returned(
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
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
                    "last_check": time.time() - 30,
                    "last_state_change": time.time(),
                    "perf_data": "",
                    "check_command": "check_mk-test",
                    "labels": {},
                    "label_sources": {},
                    "tags": {"criticality": "prod", "networking": "lan"},
                }
            ],
        )
        _expect_list_services_queries(mock_livestatus, extra_columns="tags")

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_host_services(
                hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT, fields=["tags"]
            )

        assert resp.json["services"][0]["tags"] == {
            "criticality": "prod",
            "networking": "lan",
        }

    def test_tags_are_omitted_unless_requested(
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
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
                    "last_check": time.time() - 30,
                    "last_state_change": time.time(),
                    "perf_data": "",
                    "check_command": "check_mk-test",
                    "labels": {"cmk/check_plugin": "cpu_load"},
                    "label_sources": {"cmk/check_plugin": "discovered"},
                    "tags": {"criticality": "prod"},
                }
            ],
        )
        _expect_list_services_queries(mock_livestatus)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_host_services(
                hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT
            )

        assert "tags" not in resp.json["services"][0]

    def test_labels_are_omitted_unless_requested(
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
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
                    "last_check": time.time() - 30,
                    "last_state_change": time.time(),
                    "perf_data": "",
                    "check_command": "check_mk-test",
                    "labels": {"cmk/check_plugin": "cpu_load"},
                    "label_sources": {"cmk/check_plugin": "discovered"},
                    "tags": {"criticality": "prod"},
                }
            ],
        )
        _expect_list_services_queries(mock_livestatus)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_host_services(
                hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT
            )

        assert "labels" not in resp.json["services"][0]

    def test_service_contacts_are_returned_when_requested(
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
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
                    "last_check": time.time() - 30,
                    "last_state_change": time.time(),
                    "perf_data": "",
                    "check_command": "check_mk-test",
                    "labels": {},
                    "label_sources": {},
                    "tags": {},
                    "contacts": ["hh", "ops"],
                }
            ],
        )
        _expect_list_services_queries(mock_livestatus, extra_columns="contacts")

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_host_services(
                hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT, fields=["contacts"]
            )

        assert resp.json["services"][0]["contacts"] == ["hh", "ops"]

    def test_contacts_are_omitted_unless_requested(
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
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
                    "last_check": time.time() - 30,
                    "last_state_change": time.time(),
                    "perf_data": "",
                    "check_command": "check_mk-test",
                    "labels": {},
                    "label_sources": {},
                    "tags": {},
                    "contacts": ["hh"],
                }
            ],
        )
        _expect_list_services_queries(mock_livestatus)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_host_services(
                hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT
            )

        assert "contacts" not in resp.json["services"][0]

    def test_service_contact_groups_are_returned_when_requested(
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
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
                    "last_check": time.time() - 30,
                    "last_state_change": time.time(),
                    "perf_data": "",
                    "check_command": "check_mk-test",
                    "labels": {},
                    "label_sources": {},
                    "tags": {},
                    "contacts": [],
                    "contact_groups": ["all", "linux"],
                }
            ],
        )
        _expect_list_services_queries(mock_livestatus, extra_columns="contact_groups")

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_host_services(
                hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT, fields=["contact_groups"]
            )

        assert resp.json["services"][0]["contact_groups"] == ["all", "linux"]

    def test_contact_groups_are_omitted_unless_requested(
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
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
                    "last_check": time.time() - 30,
                    "last_state_change": time.time(),
                    "perf_data": "",
                    "check_command": "check_mk-test",
                    "labels": {},
                    "label_sources": {},
                    "tags": {},
                    "contacts": [],
                    "contact_groups": ["all", "linux"],
                }
            ],
        )
        _expect_list_services_queries(mock_livestatus)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_host_services(
                hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT
            )

        assert "contact_groups" not in resp.json["services"][0]

    @pytest.mark.usefixtures("registered_perfometer")
    def test_service_with_performance_data_has_a_perfometer(
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
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
                    "last_check": time.time() - 30,
                    "last_state_change": time.time(),
                    "perf_data": "test_metric=42;;;0;100",
                    "labels": {},
                    "label_sources": {},
                    "tags": {},
                    "check_command": "check_mk-test",
                }
            ],
        )
        _expect_list_services_queries(mock_livestatus)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_host_services(
                hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT
            )

        assert resp.json["services"][0]["perfometer"] == {
            "value": 42.0,
            "value_range": {"min": 0.0, "max": 100.0},
            "formatted": "42",
            "color": "#28a2f3",
        }

    def test_service_without_performance_data_has_no_perfometer(
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
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
                    "last_check": time.time() - 30,
                    "last_state_change": time.time(),
                    "perf_data": "",
                    "labels": {},
                    "label_sources": {},
                    "tags": {},
                    "check_command": "check_mk-test",
                }
            ],
        )
        _expect_list_services_queries(mock_livestatus)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_host_services(
                hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT
            )

        assert "perfometer" not in resp.json["services"][0]

    @pytest.mark.usefixtures("registered_perfometer")
    def test_performance_data_matching_no_perfometer_is_omitted(
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
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
                    "last_check": time.time() - 30,
                    "last_state_change": time.time(),
                    "perf_data": "unknown_metric=42;;;0;100",
                    "labels": {},
                    "label_sources": {},
                    "tags": {},
                    "check_command": "check_mk-test",
                }
            ],
        )
        _expect_list_services_queries(mock_livestatus)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.list_host_services(
                hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT
            )

        assert "perfometer" not in resp.json["services"][0]

    def test_pending_service_has_no_last_check(
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
                    "perf_data": "",
                    "labels": {},
                    "label_sources": {},
                    "tags": {},
                    "check_command": "check_mk-test",
                    "host_name": _HOSTNAME,
                    "state": 0,
                    "plugin_output": "",
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
                    "last_check": 0,
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
                _DEFAULT_ORDER_BY,
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

        assert resp.json["services"][0]["last_check"] is None

    @pytest.mark.parametrize(
        "sort, expected_order_by",
        [
            pytest.param(["state:desc"], "OrderBy: state desc", id="state descending"),
            pytest.param(
                ["summary:asc"], "OrderBy: plugin_output asc natural", id="summary ascending"
            ),
            pytest.param(
                ["last_state_change:desc"],
                "OrderBy: last_state_change desc",
                id="last state change descending",
            ),
            pytest.param(
                ["state:desc", "name:asc"],
                "OrderBy: state desc",
                id="livestatus orders by the primary sorter only",
            ),
        ],
    )
    def test_requested_sort_reaches_livestatus(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
        sort: list[str],
        expected_order_by: str,
    ) -> None:
        mock_livestatus.add_table("hosts", [{"name": _HOSTNAME}])
        mock_livestatus.add_table("services", [])
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
                expected_order_by,
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
                hostname=_HOSTNAME, site_id=_SITE_ID, limit=_LIMIT, sort=sort
            )

        assert resp.json["services"] == []

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
                    "perf_data": "",
                    "labels": {},
                    "label_sources": {},
                    "tags": {},
                    "check_command": "check_mk-test",
                    "host_name": _HOSTNAME,
                    "state": 0,
                    "plugin_output": "OK - load average: 0.10, 0.05, 0.01",
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
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
                _DEFAULT_ORDER_BY,
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
                    "perf_data": "",
                    "labels": {},
                    "label_sources": {},
                    "tags": {},
                    "check_command": "check_mk-test",
                    "host_name": _HOSTNAME,
                    "state": 0,
                    "plugin_output": "OK - load average: 0.10, 0.05, 0.01",
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
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
                _DEFAULT_ORDER_BY,
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
                    "perf_data": "",
                    "labels": {},
                    "label_sources": {},
                    "tags": {},
                    "check_command": "check_mk-test",
                    "host_name": _HOSTNAME,
                    "state": 0,
                    "plugin_output": "OK - load average: 0.10, 0.05, 0.01",
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
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
                _DEFAULT_ORDER_BY,
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


class TestMonitorServiceOverview:
    @time_machine.travel("2026-07-13 11:39:00+00:00", tick=False)
    def test_returns_the_requested_service(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table(
            "services",
            [
                {
                    "description": _SERVICE_DESCRIPTION,
                    "perf_data": "",
                    "check_command": "check_mk-test",
                    "host_name": _HOSTNAME,
                    "state": 1,
                    "plugin_output": "WARN - load average: 3.10, 2.05, 1.01",
                    "last_check": time.time(),
                    "last_state_change": time.time(),
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
                    "host_alias": _HOST_ALIAS,
                    "host_state": 0,
                    "host_acknowledged": 0,
                    "host_scheduled_downtime_depth": 0,
                    "contact_groups": ["all"],
                    "long_plugin_output": "15 min load: 0.01 (per core: 0.01)",
                    "current_attempt": 2,
                    "max_check_attempts": 4,
                    "next_check": time.time() + 60,
                    "contacts": ["hh"],
                    "tags": {"criticality": "prod"},
                    "labels": {"cmk/check_plugin": "cpu_load"},
                    "label_sources": {"cmk/check_plugin": "discovered"},
                }
            ],
        )
        mock_livestatus.expect_query(
            [
                "GET services",
                f"Columns: {_SERVICE_OVERVIEW_COLUMNS}",
                f"Filter: host_name = {_HOSTNAME}",
                f"Filter: description = {_SERVICE_DESCRIPTION}",
                "And: 2",
            ],
            sites=[_SITE_ID],
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get_service_overview(
                hostname=_HOSTNAME, site_id=_SITE_ID, service_name=_SERVICE_DESCRIPTION
            )

        assert resp.json["name"] == _SERVICE_DESCRIPTION
        assert resp.json["host_name"] == _HOSTNAME
        assert resp.json["site_id"] == _SITE_ID
        assert resp.json["state"] == "WARN"
        assert resp.json["modes"] == []
        assert resp.json["host_alias"] == _HOST_ALIAS
        assert resp.json["host_state"] == "UP"
        assert resp.json["contact_groups"] == ["all"]
        assert resp.json["summary"] == "WARN - load average: 3.10, 2.05, 1.01"
        assert resp.json["long_output"] == "15 min load: 0.01 (per core: 0.01)"
        assert resp.json["last_check"] == 1783942740
        assert resp.json["last_state_change"] == 1783942740
        assert resp.json["current_attempt"] == 2
        assert resp.json["max_check_attempts"] == 4
        assert resp.json["next_check"] == 1783942800
        assert resp.json["tags"] == {"criticality": "prod"}
        assert resp.json["labels"] == {
            "cmk/check_plugin": {"value": "cpu_load", "source": "discovered"}
        }
        assert resp.json["legacy_host_status_link"] == (
            f"view.py?view_name=hoststatus&site={_SITE_ID}&host={_HOSTNAME}"
        )
        assert resp.json["legacy_service_status_link"] == (
            f"view.py?view_name=service&site={_SITE_ID}&host={_HOSTNAME}&service=CPU+load"
        )
        assert resp.json["legacy_service_graphs_link"] == (
            f"view.py?view_name=service_graphs&site={_SITE_ID}&host={_HOSTNAME}&service=CPU+load"
        )

    @pytest.mark.parametrize(
        "columns, expected_icons",
        [
            pytest.param(
                {"scheduled_downtime_depth": 1},
                ["downtime"],
                id="in scheduled downtime",
            ),
            pytest.param({"acknowledged": 1}, ["ack"], id="problem acknowledged"),
            pytest.param(
                {"notifications_enabled": 0},
                ["notif-disabled"],
                id="notifications disabled",
            ),
            pytest.param(
                {"scheduled_downtime_depth": 2, "acknowledged": 1, "notifications_enabled": 0},
                ["downtime", "ack", "notif-disabled"],
                id="all modes at once",
            ),
        ],
    )
    @time_machine.travel("2026-07-13 11:39:00+00:00", tick=False)
    def test_modes_reflect_the_service_state(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
        columns: dict[str, int],
        expected_icons: list[str],
    ) -> None:
        mock_livestatus.add_table(
            "services",
            [
                {
                    "description": _SERVICE_DESCRIPTION,
                    "perf_data": "",
                    "check_command": "check_mk-test",
                    "host_name": _HOSTNAME,
                    "state": 2,
                    "plugin_output": "CRIT - load average: 9.10, 8.05, 7.01",
                    "last_check": time.time(),
                    "last_state_change": time.time(),
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
                    "host_alias": _HOST_ALIAS,
                    "host_state": 0,
                    "host_acknowledged": 0,
                    "host_scheduled_downtime_depth": 0,
                    "contact_groups": ["all"],
                    "long_plugin_output": "15 min load: 0.01 (per core: 0.01)",
                    "current_attempt": 2,
                    "max_check_attempts": 4,
                    "next_check": time.time() + 60,
                    "contacts": ["hh"],
                    "tags": {"criticality": "prod"},
                    "labels": {"cmk/check_plugin": "cpu_load"},
                    "label_sources": {"cmk/check_plugin": "discovered"},
                    **columns,
                }
            ],
        )
        mock_livestatus.expect_query(
            [
                "GET services",
                f"Columns: {_SERVICE_OVERVIEW_COLUMNS}",
                f"Filter: host_name = {_HOSTNAME}",
                f"Filter: description = {_SERVICE_DESCRIPTION}",
                "And: 2",
            ],
            sites=[_SITE_ID],
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get_service_overview(
                hostname=_HOSTNAME, site_id=_SITE_ID, service_name=_SERVICE_DESCRIPTION
            )

        assert [mode["icon_name"] for mode in resp.json["modes"]] == expected_icons

    @time_machine.travel("2026-07-13 11:39:00+00:00", tick=False)
    def test_passive_service_has_no_next_check(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table(
            "services",
            [
                {
                    "description": _SERVICE_DESCRIPTION,
                    "perf_data": "",
                    "check_command": "check_mk-test",
                    "host_name": _HOSTNAME,
                    "state": 0,
                    "plugin_output": "OK - load average: 0.10, 0.05, 0.01",
                    "last_check": time.time(),
                    "last_state_change": time.time(),
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
                    "host_alias": _HOST_ALIAS,
                    "host_state": 0,
                    "host_acknowledged": 0,
                    "host_scheduled_downtime_depth": 0,
                    "contact_groups": ["all"],
                    "long_plugin_output": "",
                    "current_attempt": 1,
                    "max_check_attempts": 1,
                    "next_check": 0,
                    "contacts": ["hh"],
                    "labels": {},
                    "label_sources": {},
                    "tags": {},
                }
            ],
        )
        mock_livestatus.expect_query(
            [
                "GET services",
                f"Columns: {_SERVICE_OVERVIEW_COLUMNS}",
                f"Filter: host_name = {_HOSTNAME}",
                f"Filter: description = {_SERVICE_DESCRIPTION}",
                "And: 2",
            ],
            sites=[_SITE_ID],
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get_service_overview(
                hostname=_HOSTNAME, site_id=_SITE_ID, service_name=_SERVICE_DESCRIPTION
            )

        assert resp.json["next_check"] is None

    @time_machine.travel("2026-07-13 11:39:00+00:00", tick=False)
    def test_pending_service_has_no_last_check(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table(
            "services",
            [
                {
                    "description": _SERVICE_DESCRIPTION,
                    "perf_data": "",
                    "check_command": "check_mk-test",
                    "host_name": _HOSTNAME,
                    "state": 0,
                    "plugin_output": "",
                    "last_check": 0,
                    "last_state_change": time.time(),
                    "acknowledged": 0,
                    "scheduled_downtime_depth": 0,
                    "notifications_enabled": 1,
                    "is_flapping": 0,
                    "staleness": 0.0,
                    "host_alias": _HOST_ALIAS,
                    "host_state": 0,
                    "host_acknowledged": 0,
                    "host_scheduled_downtime_depth": 0,
                    "contact_groups": ["all"],
                    "long_plugin_output": "",
                    "current_attempt": 1,
                    "max_check_attempts": 1,
                    "next_check": time.time() + 60,
                    "contacts": ["hh"],
                    "labels": {},
                    "label_sources": {},
                    "tags": {},
                }
            ],
        )
        mock_livestatus.expect_query(
            [
                "GET services",
                f"Columns: {_SERVICE_OVERVIEW_COLUMNS}",
                f"Filter: host_name = {_HOSTNAME}",
                f"Filter: description = {_SERVICE_DESCRIPTION}",
                "And: 2",
            ],
            sites=[_SITE_ID],
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get_service_overview(
                hostname=_HOSTNAME, site_id=_SITE_ID, service_name=_SERVICE_DESCRIPTION
            )

        assert resp.json["last_check"] is None

    def test_unknown_service_returns_404(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("services", [])
        mock_livestatus.expect_query(
            [
                "GET services",
                f"Columns: {_SERVICE_OVERVIEW_COLUMNS}",
                f"Filter: host_name = {_HOSTNAME}",
                "Filter: description = not-a-service",
                "And: 2",
            ],
            sites=[_SITE_ID],
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get_service_overview(
                hostname=_HOSTNAME,
                site_id=_SITE_ID,
                service_name="not-a-service",
                expect_ok=False,
            )

        assert resp.status_code == 404

    def test_unknown_site_is_rejected(self, clients: ClientRegistry) -> None:
        resp = clients.MonitorHosts.get_service_overview(
            hostname=_HOSTNAME,
            site_id="no-such-site",
            service_name=_SERVICE_DESCRIPTION,
            expect_ok=False,
        )
        assert resp.status_code == 400

    def test_invalid_credentials(self, clients: ClientRegistry) -> None:
        client = clients.MonitorHosts
        client.set_credentials("foouser", "barpassword")

        resp = client.get_service_overview(
            hostname=_HOSTNAME,
            site_id=_SITE_ID,
            service_name=_SERVICE_DESCRIPTION,
            expect_ok=False,
        )

        assert resp.status_code == 401
        assert "credentials" in resp.json["detail"]


class TestMonitorHostServicesReschedule:
    def test_reschedule_sends_forced_check_command(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.expect_query(
            f"COMMAND [...] SCHEDULE_FORCED_SVC_CHECK;{_HOSTNAME};{_SERVICE_DESCRIPTION};...",
            match_type="ellipsis",
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.reschedule_services(
                services=[
                    {
                        "site_id": _SITE_ID,
                        "host_name": _HOSTNAME,
                        "name": _SERVICE_DESCRIPTION,
                    }
                ]
            )

        assert resp.json["rescheduled"] == 1

    def test_reschedule_sends_one_command_per_service(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.expect_query(
            f"COMMAND [...] SCHEDULE_FORCED_SVC_CHECK;{_HOSTNAME};{_SERVICE_DESCRIPTION};...",
            match_type="ellipsis",
        )
        mock_livestatus.expect_query(
            f"COMMAND [...] SCHEDULE_FORCED_SVC_CHECK;{_HOSTNAME};Memory;...",
            match_type="ellipsis",
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.reschedule_services(
                services=[
                    {
                        "site_id": _SITE_ID,
                        "host_name": _HOSTNAME,
                        "name": _SERVICE_DESCRIPTION,
                    },
                    {"site_id": _SITE_ID, "host_name": _HOSTNAME, "name": "Memory"},
                ],
                spread_minutes=5,
            )

        assert resp.json["rescheduled"] == 2

    def test_reschedule_without_services_touches_no_site(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.reschedule_services(services=[])

        assert resp.json["rescheduled"] == 0

    def test_negative_spread_is_rejected(self, clients: ClientRegistry) -> None:
        resp = clients.MonitorHosts.reschedule_services(
            services=[{"site_id": _SITE_ID, "host_name": _HOSTNAME, "name": _SERVICE_DESCRIPTION}],
            spread_minutes=-1,
            expect_ok=False,
        )

        assert resp.status_code == 400

    def test_invalid_credentials(self, clients: ClientRegistry) -> None:
        client = clients.MonitorHosts
        client.set_credentials("foouser", "barpassword")

        resp = client.reschedule_services(
            services=[{"site_id": _SITE_ID, "host_name": _HOSTNAME, "name": _SERVICE_DESCRIPTION}],
            expect_ok=False,
        )

        assert resp.status_code == 401
        assert "credentials" in resp.json["detail"]


class TestMonitorServiceActionMenu:
    def test_unknown_site_is_rejected(self, clients: ClientRegistry) -> None:
        resp = clients.MonitorHosts.service_action_menu(
            hostname=_HOSTNAME,
            site_id="no-such-site",
            service_name=_SERVICE_DESCRIPTION,
            expect_ok=False,
        )

        assert resp.status_code == 400

    def test_missing_service_returns_404(
        self,
        clients: ClientRegistry,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        mock_livestatus.add_table("services", [])
        mock_livestatus.expect_query(
            [
                "GET services",
                f"Filter: host_name = {_HOSTNAME}",
                "Filter: service_description = No such service",
            ],
            match_type="loose",
            sites=[_SITE_ID],
        )

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.service_action_menu(
                hostname=_HOSTNAME,
                site_id=_SITE_ID,
                service_name="No such service",
                expect_ok=False,
            )

        assert resp.status_code == 404

    def test_invalid_credentials(self, clients: ClientRegistry) -> None:
        client = clients.MonitorHosts
        client.set_credentials("foouser", "barpassword")

        resp = client.service_action_menu(
            hostname=_HOSTNAME,
            site_id=_SITE_ID,
            service_name=_SERVICE_DESCRIPTION,
            expect_ok=False,
        )

        assert resp.status_code == 401
        assert "credentials" in resp.json["detail"]


_SITE_ID = "NO_SITE"
_HOSTNAME = "heute"
_SERVICE_DESCRIPTION = "CPU load"
_HOST_ALIAS = "Web Server"
_SERVICE_OVERVIEW_COLUMNS = (
    "description host_name state plugin_output last_check last_state_change acknowledged "
    "scheduled_downtime_depth notifications_enabled is_flapping staleness host_alias host_state "
    "host_acknowledged host_scheduled_downtime_depth contact_groups long_plugin_output "
    "current_attempt max_check_attempts next_check tags labels label_sources perf_data "
    "check_command"
)
_LIMIT = 1000
_SERVICES_COLUMNS = (
    "description host_name state plugin_output acknowledged scheduled_downtime_depth "
    "notifications_enabled is_flapping staleness last_check last_state_change perf_data "
    "check_command"
)
_DEFAULT_ORDER_BY = "OrderBy: description asc natural"


def _expect_list_services_queries(
    mock_livestatus: MockLiveStatusConnection, *, extra_columns: str = ""
) -> None:
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
            f"Columns: {_SERVICES_COLUMNS}{' ' + extra_columns if extra_columns else ''}",
            f"Filter: host_name = {_HOSTNAME}",
            _DEFAULT_ORDER_BY,
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

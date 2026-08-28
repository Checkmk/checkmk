#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
import time_machine

from cmk.gui.monitor.hosts._api._events import (
    _DEFAULT_LIMIT,
    _DEFAULT_TIME_WINDOW_DAYS,
    _MAX_LIMIT,
    _MAX_TIME_WINDOW_DAYS,
    _SECONDS_PER_DAY,
)
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.rest_api_client import ClientRegistry

_SITE_ID = "NO_SITE"

_HOSTNAME = "web-server-01"

_NOW = 1_752_400_000

_LOG_TABLE_COLUMNS = (
    "time lineno type state state_type state_info command_name plugin_output service_description"
)

_HOSTS = [{"name": _HOSTNAME, "state": 0}]

_EVENTS = [
    {
        "time": _NOW - 3600,
        "lineno": 10,
        "type": "SERVICE ALERT",
        "state": 2,
        "state_type": "HARD",
        "state_info": "CRIT",
        "command_name": "",
        "plugin_output": "CRIT - load average: 12.10",
        "service_description": "CPU load",
        "host_name": _HOSTNAME,
        "class": 1,
    },
    {
        "time": _NOW - 1800,
        "lineno": 20,
        "type": "HOST ALERT",
        "state": 1,
        "state_type": "HARD",
        "state_info": "DOWN",
        "command_name": "",
        "plugin_output": "CRIT - 100% packet loss",
        "service_description": "",
        "host_name": _HOSTNAME,
        "class": 1,
    },
    {
        "time": _NOW - 900,
        "lineno": 30,
        "type": "SERVICE NOTIFICATION",
        "state": 2,
        "state_type": "",
        "state_info": "",
        "command_name": "check-mk-notify",
        "plugin_output": "CRIT - load average: 12.10",
        "service_description": "CPU load",
        "host_name": _HOSTNAME,
        "class": 3,
    },
]


def _expected_since(days: int = _DEFAULT_TIME_WINDOW_DAYS) -> int:
    return _NOW - days * _SECONDS_PER_DAY


def _expect_host_exists(mock_livestatus: MockLiveStatusConnection) -> None:
    mock_livestatus.expect_query(
        ["GET hosts", "Columns: name", f"Filter: name = {_HOSTNAME}", "Limit: 1"],
        sites=[_SITE_ID],
    )


def _expect_event_query(
    mock_livestatus: MockLiveStatusConnection,
    *,
    service_name: str | None = None,
    since: int | None = None,
    limit: int = _DEFAULT_LIMIT,
) -> None:
    service_filter = (
        [] if service_name is None else [f"Filter: service_description = {service_name}"]
    )
    mock_livestatus.expect_query(
        [
            "GET log",
            f"Columns: {_LOG_TABLE_COLUMNS}",
            f"Filter: time >= {_expected_since() if since is None else since}",
            f"Filter: host_name = {_HOSTNAME}",
            "Filter: class = 1",
            "Filter: class = 3",
            "Filter: class = 8",
            "Or: 3",
            *service_filter,
            f"And: {3 + len(service_filter)}",
            "OrderBy: time desc",
            f"Limit: {limit + 1}",
        ],
        sites=[_SITE_ID],
    )


class TestMonitorHostEventsQueryParamValidation:
    def test_unknown_site_is_rejected(self, clients: ClientRegistry) -> None:
        resp = clients.MonitorHosts.get_events(_HOSTNAME, site_id="no-such-site", expect_ok=False)
        assert resp.status_code == 400

    @pytest.mark.parametrize(
        "time_window_days",
        [
            pytest.param(0, id="below the lower bound"),
            pytest.param(_MAX_TIME_WINDOW_DAYS + 1, id="above the upper bound"),
        ],
    )
    def test_invalid_time_window(self, clients: ClientRegistry, time_window_days: int) -> None:
        resp = clients.MonitorHosts.get_events(
            _HOSTNAME, site_id=_SITE_ID, time_window_days=time_window_days, expect_ok=False
        )
        assert resp.status_code == 400

    @pytest.mark.parametrize(
        "limit",
        [
            pytest.param(0, id="below the lower bound"),
            pytest.param(_MAX_LIMIT + 1, id="above the upper bound"),
        ],
    )
    def test_invalid_limit(self, clients: ClientRegistry, limit: int) -> None:
        resp = clients.MonitorHosts.get_events(
            _HOSTNAME, site_id=_SITE_ID, limit=limit, expect_ok=False
        )
        assert resp.status_code == 400


class TestMonitorHostEvents:
    def test_unknown_host_is_not_found(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        mock_livestatus.add_table("hosts", [])
        _expect_host_exists(mock_livestatus)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get_events(_HOSTNAME, site_id=_SITE_ID, expect_ok=False)

        assert resp.status_code == 404

    @time_machine.travel(_NOW)
    def test_events_of_a_host_include_its_services(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.add_table("log", _EVENTS)
        _expect_host_exists(mock_livestatus)
        _expect_event_query(mock_livestatus)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get_events(_HOSTNAME, site_id=_SITE_ID)

        assert resp.status_code == 200
        assert [event["service_name"] for event in resp.json["events"]] == [
            "CPU load",
            None,
            "CPU load",
        ]

    @time_machine.travel(_NOW)
    def test_events_come_newest_first(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.add_table("log", _EVENTS)
        _expect_host_exists(mock_livestatus)
        _expect_event_query(mock_livestatus)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get_events(_HOSTNAME, site_id=_SITE_ID)

        assert [event["time"] for event in resp.json["events"]] == [
            _NOW - 900,
            _NOW - 1800,
            _NOW - 3600,
        ]

    @time_machine.travel(_NOW)
    def test_icons_are_resolved_server_side(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.add_table("log", _EVENTS)
        _expect_host_exists(mock_livestatus)
        _expect_event_query(mock_livestatus)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get_events(_HOSTNAME, site_id=_SITE_ID)

        assert [event["icon"] for event in resp.json["events"]] == [
            {"icon_name": "alert-cmk-notify", "title": "Core produced a notification"},
            {"icon_name": "alert-down", "title": "Host alert"},
            {"icon_name": "alert-crit", "title": "Service alert"},
        ]

    @time_machine.travel(_NOW)
    def test_the_time_window_defaults_to_eight_days(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.add_table("log", _EVENTS)
        _expect_host_exists(mock_livestatus)
        _expect_event_query(mock_livestatus, since=_NOW - 8 * _SECONDS_PER_DAY)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get_events(_HOSTNAME, site_id=_SITE_ID)

        assert resp.json["meta"]["since"] == _NOW - 8 * _SECONDS_PER_DAY
        assert resp.json["meta"]["time_window_days"] == 8

    @time_machine.travel(_NOW)
    def test_the_time_window_is_a_parameter(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.add_table("log", _EVENTS)
        _expect_host_exists(mock_livestatus)
        _expect_event_query(mock_livestatus, since=_NOW - 30 * _SECONDS_PER_DAY)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get_events(_HOSTNAME, site_id=_SITE_ID, time_window_days=30)

        assert resp.json["meta"]["since"] == _NOW - 30 * _SECONDS_PER_DAY
        assert resp.json["meta"]["time_window_days"] == 30

    @time_machine.travel(_NOW)
    def test_a_service_name_narrows_the_events_to_that_service(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.add_table("log", _EVENTS)
        _expect_host_exists(mock_livestatus)
        _expect_event_query(mock_livestatus, service_name="CPU load")

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get_events(
                _HOSTNAME, site_id=_SITE_ID, service_name="CPU load"
            )

        assert [event["service_name"] for event in resp.json["events"]] == ["CPU load", "CPU load"]

    @time_machine.travel(_NOW)
    def test_the_row_limit_is_reported_when_it_cuts_off_events(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.add_table("log", _EVENTS)
        _expect_host_exists(mock_livestatus)
        _expect_event_query(mock_livestatus, limit=2)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get_events(_HOSTNAME, site_id=_SITE_ID, limit=2)

        assert len(resp.json["events"]) == 2
        assert resp.json["meta"]["truncated"] is True
        assert resp.json["meta"]["limit"] == 2

    @time_machine.travel(_NOW)
    def test_a_complete_list_is_not_truncated(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.add_table("log", _EVENTS)
        _expect_host_exists(mock_livestatus)
        _expect_event_query(mock_livestatus)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get_events(_HOSTNAME, site_id=_SITE_ID)

        assert resp.json["meta"]["truncated"] is False

    @time_machine.travel(_NOW)
    def test_the_whole_host_links_to_the_legacy_host_events_view(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.add_table("log", _EVENTS)
        _expect_host_exists(mock_livestatus)
        _expect_event_query(mock_livestatus)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get_events(_HOSTNAME, site_id=_SITE_ID)

        assert resp.json["meta"]["legacy_events_link"] == (
            f"view.py?view_name=hostsvcevents&site={_SITE_ID}&host={_HOSTNAME}"
        )

    @time_machine.travel(_NOW)
    def test_a_single_service_links_to_the_legacy_service_events_view(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.add_table("log", _EVENTS)
        _expect_host_exists(mock_livestatus)
        _expect_event_query(mock_livestatus, service_name="CPU load")

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get_events(
                _HOSTNAME, site_id=_SITE_ID, service_name="CPU load"
            )

        assert resp.json["meta"]["legacy_events_link"] == (
            f"view.py?view_name=svcevents&site={_SITE_ID}&host={_HOSTNAME}&service=CPU+load"
        )

    @time_machine.travel(_NOW)
    def test_state_info_falls_back_to_the_state_type(
        self, clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        mock_livestatus.add_table("hosts", _HOSTS)
        mock_livestatus.add_table("log", [{**_EVENTS[0], "state_info": "", "state_type": "SOFT"}])
        _expect_host_exists(mock_livestatus)
        _expect_event_query(mock_livestatus)

        with mock_livestatus(expect_status_query=True):
            resp = clients.MonitorHosts.get_events(_HOSTNAME, site_id=_SITE_ID)

        assert resp.json["events"][0]["state_info"] == "SOFT"

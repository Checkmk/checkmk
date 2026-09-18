#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.gui.monitor.hosts._api._event_icons import EventIcon
from cmk.gui.monitor.hosts._api._events import _handle_get_host_events, _SECONDS_PER_DAY
from cmk.gui.monitor.hosts._impl import _build_event_filter
from cmk.gui.monitor.hosts._models import Event
from cmk.gui.openapi.utils import ProblemException

from .testlib import get_fake_event_repository, get_fake_host_repository

_SINCE = 1_000_000


def _event(
    *,
    time: int = _SINCE + 100,
    lineno: int = 1,
    event_type: str = "SERVICE ALERT",
    state: int = 2,
    state_type: str = "HARD",
    state_info: str = "CRIT",
    command_name: str = "",
    plugin_output: str = "CRIT - load average: 12.10",
    service_name: str | None = "CPU load",
) -> Event:
    return Event(
        time=time,
        lineno=lineno,
        type=event_type,
        state=state,
        state_type=state_type,
        state_info=state_info,
        command_name=command_name,
        plugin_output=plugin_output,
        service_name=service_name,
    )


class TestEventsResponse:
    def test_unknown_host_is_not_found(self) -> None:
        with pytest.raises(ProblemException, match="404"):
            _handle_get_host_events(
                get_fake_host_repository(hostnames=["web-server-01"]),
                get_fake_event_repository([]),
                hostname="does-not-exist",
                site_id="local",
                since=_SINCE,
            )

    def test_a_host_without_events_returns_an_empty_list(self) -> None:
        response = _handle_get_host_events(
            get_fake_host_repository(hostnames=["web-server-01"]),
            get_fake_event_repository([]),
            hostname="web-server-01",
            site_id="local",
            since=_SINCE,
        )

        assert response.events == []
        assert response.meta.truncated is False

    def test_the_time_window_days_is_reported(self) -> None:
        response = _handle_get_host_events(
            get_fake_host_repository(hostnames=["web-server-01"]),
            get_fake_event_repository([]),
            hostname="web-server-01",
            site_id="local",
            since=_SINCE,
            time_window_days=30,
        )

        assert response.meta.time_window_days == 30

    def test_events_come_newest_first(self) -> None:
        events = [
            _event(time=_SINCE + 1, lineno=1),
            _event(time=_SINCE + 3, lineno=7),
            _event(time=_SINCE + 3, lineno=9),
            _event(time=_SINCE + 2, lineno=4),
        ]

        response = _handle_get_host_events(
            get_fake_host_repository(hostnames=["web-server-01"]),
            get_fake_event_repository(events),
            hostname="web-server-01",
            site_id="local",
            since=_SINCE,
        )

        assert [entry.time for entry in response.events] == [
            _SINCE + 3,
            _SINCE + 3,
            _SINCE + 2,
            _SINCE + 1,
        ]

    def test_the_limit_cuts_off_the_oldest_events_and_is_reported(self) -> None:
        events = [_event(time=_SINCE + offset, lineno=offset) for offset in range(1, 6)]

        response = _handle_get_host_events(
            get_fake_host_repository(hostnames=["web-server-01"]),
            get_fake_event_repository(events),
            hostname="web-server-01",
            site_id="local",
            since=_SINCE,
            limit=2,
        )

        assert [entry.time for entry in response.events] == [_SINCE + 5, _SINCE + 4]
        assert response.meta.truncated is True
        assert response.meta.limit == 2

    def test_a_truncated_response_reports_the_window_down_to_its_oldest_shown_event(self) -> None:
        events = [_event(time=_SINCE + 100, lineno=1), _event(time=_SINCE + 50, lineno=2)]

        response = _handle_get_host_events(
            get_fake_host_repository(hostnames=["web-server-01"]),
            get_fake_event_repository(events),
            hostname="web-server-01",
            site_id="local",
            since=_SINCE,
            time_window_days=8,
            limit=1,
            # Oldest shown event (the only one, given the limit) is _SINCE + 100. Two days and
            # a second later than that rounds up to three days covered, not the requested eight.
            now=_SINCE + 100 + 2 * _SECONDS_PER_DAY + 1,
        )

        assert response.meta.truncated is True
        assert response.meta.time_window_days == 3

    def test_a_truncated_response_still_covering_today_reports_one_day(self) -> None:
        events = [_event(time=_SINCE + 100, lineno=1), _event(time=_SINCE + 50, lineno=2)]

        response = _handle_get_host_events(
            get_fake_host_repository(hostnames=["web-server-01"]),
            get_fake_event_repository(events),
            hostname="web-server-01",
            site_id="local",
            since=_SINCE,
            time_window_days=8,
            limit=1,
            now=_SINCE + 100,
        )

        assert response.meta.time_window_days == 1

    def test_a_full_page_without_more_rows_is_not_truncated(self) -> None:
        events = [_event(time=_SINCE + offset, lineno=offset) for offset in range(1, 3)]

        response = _handle_get_host_events(
            get_fake_host_repository(hostnames=["web-server-01"]),
            get_fake_event_repository(events),
            hostname="web-server-01",
            site_id="local",
            since=_SINCE,
            limit=2,
        )

        assert len(response.events) == 2
        assert response.meta.truncated is False

    def test_a_service_name_narrows_the_events_to_that_service(self) -> None:
        events = [
            _event(service_name=None, event_type="HOST ALERT"),
            _event(service_name="CPU load"),
            _event(service_name="Memory"),
        ]

        response = _handle_get_host_events(
            get_fake_host_repository(hostnames=["web-server-01"]),
            get_fake_event_repository(events),
            hostname="web-server-01",
            site_id="local",
            service_name="CPU load",
            since=_SINCE,
        )

        assert [entry.service_name for entry in response.events] == ["CPU load"]

    def test_events_of_the_whole_host_link_to_the_legacy_host_view(self) -> None:
        response = _handle_get_host_events(
            get_fake_host_repository(hostnames=["web-server-01"]),
            get_fake_event_repository([]),
            hostname="web-server-01",
            site_id="local",
            since=_SINCE,
        )

        assert response.meta.legacy_events_link == (
            "view.py?view_name=hostsvcevents&site=local&host=web-server-01"
        )

    def test_events_of_one_service_link_to_the_legacy_service_view(self) -> None:
        response = _handle_get_host_events(
            get_fake_host_repository(hostnames=["web-server-01"]),
            get_fake_event_repository([]),
            hostname="web-server-01",
            site_id="local",
            service_name="CPU load",
            since=_SINCE,
        )

        assert response.meta.legacy_events_link == (
            "view.py?view_name=svcevents&site=local&host=web-server-01&service=CPU+load"
        )

    def test_a_service_event_links_to_the_legacy_service_event_history(self) -> None:
        response = _handle_get_host_events(
            get_fake_host_repository(hostnames=["web-server-01"]),
            get_fake_event_repository([_event(service_name="CPU load")]),
            hostname="web-server-01",
            site_id="local",
            since=_SINCE,
        )

        assert response.events[0].service_link == (
            "view.py?view_name=svcevents&site=local&host=web-server-01&service=CPU+load"
        )

    def test_a_host_event_has_no_service_link(self) -> None:
        response = _handle_get_host_events(
            get_fake_host_repository(hostnames=["web-server-01"]),
            get_fake_event_repository([_event(service_name=None, event_type="HOST ALERT")]),
            hostname="web-server-01",
            site_id="local",
            since=_SINCE,
        )

        assert response.events[0].service_link is None

    def test_state_info_falls_back_to_the_state_type(self) -> None:
        response = _handle_get_host_events(
            get_fake_host_repository(hostnames=["web-server-01"]),
            get_fake_event_repository([_event(state_info="", state_type="SOFT")]),
            hostname="web-server-01",
            site_id="local",
            since=_SINCE,
        )

        assert response.events[0].state_info == "SOFT"


class TestEventIcon:
    @pytest.mark.parametrize(
        "event, expected_name, expected_title",
        [
            pytest.param(
                _event(event_type="SERVICE ALERT", state=0),
                "alert-ok",
                "Service alert",
                id="service alert OK",
            ),
            pytest.param(
                _event(event_type="SERVICE ALERT", state=3),
                "alert-unknown",
                "Service alert",
                id="service alert UNKNOWN",
            ),
            pytest.param(
                _event(event_type="HOST ALERT", state=1),
                "alert-down",
                "Host alert",
                id="host alert DOWN",
            ),
            pytest.param(
                _event(event_type="HOST ALERT", state=2),
                "alert-unreach",
                "Host alert",
                id="host alert UNREACHABLE",
            ),
            pytest.param(
                _event(event_type="SERVICE ALERT HANDLER STARTED"),
                "alert-alert-handler-started",
                "Alert handler started",
                id="alert handler started",
            ),
            pytest.param(
                _event(event_type="SERVICE ALERT HANDLER STOPPED", state=0),
                "alert-alert-handler-stopped",
                "Alert handler stopped",
                id="alert handler stopped",
            ),
            pytest.param(
                _event(event_type="SERVICE ALERT HANDLER STOPPED", state=1),
                "alert-alert-handler-failed",
                "Alert handler failed",
                id="alert handler failed",
            ),
            pytest.param(
                _event(event_type="SERVICE DOWNTIME ALERT", state_type="STARTED"),
                "alert-downtime",
                "Downtime",
                id="downtime started",
            ),
            pytest.param(
                _event(event_type="HOST DOWNTIME ALERT", state_type="END"),
                "alert-downtimestop",
                "Downtime stopped",
                id="downtime ended",
            ),
            pytest.param(
                _event(event_type="SERVICE NOTIFICATION", command_name="check-mk-notify"),
                "alert-cmk-notify",
                "Core produced a notification",
                id="notification produced by the core",
            ),
            pytest.param(
                _event(event_type="HOST NOTIFICATION", command_name="mail"),
                "alert-notify",
                "User notification",
                id="notification sent to a user",
            ),
            pytest.param(
                _event(event_type="SERVICE NOTIFICATION RESULT"),
                "alert-notify-result",
                "Final notification result",
                id="notification result",
            ),
            pytest.param(
                _event(event_type="SERVICE NOTIFICATION PROGRESS"),
                "alert-notify-progress",
                "The notification is being processed",
                id="notification progress",
            ),
            pytest.param(
                _event(event_type="EXTERNAL COMMAND"),
                "alert-command",
                "External command",
                id="external command",
            ),
            pytest.param(
                _event(event_type="Warning: Checkmk Monitoring Core restarting..."),
                "alert-restart",
                "Core restarted",
                id="core restart wins over the plain 'starting...' match",
            ),
            pytest.param(
                _event(event_type="Reloading configuration Check_MK version 2.6"),
                "alert-reload",
                "Core configuration reloaded",
                id="core configuration reloaded",
            ),
            pytest.param(
                _event(event_type="Check_MK Micro Core starting..."),
                "alert-start",
                "Core started",
                id="core started",
            ),
            pytest.param(
                _event(event_type="Check_MK Micro Core shutting down"),
                "alert-stop",
                "Core stopped",
                id="core stopped",
            ),
            pytest.param(
                _event(event_type="SERVICE FLAPPING ALERT"),
                "alert-flapping",
                "Flapping",
                id="flapping",
            ),
            pytest.param(
                _event(event_type="HOST ACKNOWLEDGE ALERT", state_type="STARTED"),
                "alert-ack",
                "Acknowledged",
                id="acknowledgement started",
            ),
            pytest.param(
                _event(event_type="HOST ACKNOWLEDGE ALERT", state_type="STOPPED"),
                "alert-ackstop",
                "Stopped acknowledgment",
                id="acknowledgement stopped",
            ),
        ],
    )
    def test_resolves_the_icon_of_an_event(
        self, event: Event, expected_name: str, expected_title: str
    ) -> None:
        icon = EventIcon.from_event(event)

        assert icon == EventIcon(icon_name=expected_name, title=expected_title)

    @pytest.mark.parametrize(
        "event",
        [
            pytest.param(
                _event(event_type="SERVICE ALERT", state=9), id="alert in an unknown state"
            ),
            pytest.param(
                _event(event_type="HOST ALERT", state=9), id="host alert in an unknown state"
            ),
            pytest.param(_event(event_type="LOG VERSION"), id="event type without an icon"),
        ],
    )
    def test_an_event_without_an_icon_resolves_to_none(self, event: Event) -> None:
        assert EventIcon.from_event(event) is None


class TestEventFilter:
    def test_filters_the_host_and_the_log_classes(self) -> None:
        rendered = [
            ": ".join(line)
            for line in _build_event_filter(
                hostname="web-server-01", service_name=None, since=_SINCE
            ).render()
        ]

        assert rendered == [
            f"Filter: time >= {_SINCE}",
            "Filter: host_name = web-server-01",
            "Filter: class = 1",
            "Filter: class = 3",
            "Filter: class = 8",
            "Or: 3",
            "And: 3",
        ]

    def test_a_service_name_adds_a_service_filter(self) -> None:
        rendered = [
            ": ".join(line)
            for line in _build_event_filter(
                hostname="web-server-01", service_name="CPU load", since=_SINCE
            ).render()
        ]

        assert "Filter: service_description = CPU load" in rendered
        assert rendered[-1] == "And: 4"

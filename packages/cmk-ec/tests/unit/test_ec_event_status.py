#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Keeping the status of the events, also across restarts of the EC"""

import logging
from collections.abc import Callable, Sequence

import pytest

import cmk.ec.export as ec
from cmk.ec.config import Config, ExpectInterval
from cmk.ec.history import History
from cmk.ec.main import EventServer, EventStatus
from cmk.ec.perfcounters import Perfcounters

from .helpers import FakeConnection, new_event, new_host

type _Restart = Callable[[], EventStatus]


@pytest.fixture(name="restart")
def fixture_restart(
    settings: ec.Settings,
    config: Config,
    perfcounters: Perfcounters,
    history: History,
    core_connection: FakeConnection,
    event_server: EventServer,
) -> _Restart:
    """Returns the event status of a restarted EC, i.e. the loaded status saved before"""

    def restart() -> EventStatus:
        event_status = EventStatus(
            settings,
            config,
            perfcounters,
            history,
            logging.getLogger("cmk.mkeventd.EventStatus"),
            core_connection,
        )
        event_status.load_status(event_server)
        return event_status

    return restart


def _save_status_of_old_version(settings: ec.Settings, events: Sequence[object]) -> None:
    settings.paths.status_file.value.write_text(
        repr({"next_event_id": len(events) + 1, "events": events, "rule_stats": {}})
    )


def test_saved_events_are_restored_after_a_restart(
    event_status: EventStatus, restart: _Restart
) -> None:
    event_status.new_event(new_event(ec.Event(text="disk full")))
    event_status.save_status()

    restarted_event_status = restart()

    assert [event["text"] for event in restarted_event_status.events()] == ["disk full"]


def test_event_ids_continue_after_a_restart(event_status: EventStatus, restart: _Restart) -> None:
    event_status.new_event(new_event(ec.Event(text="before restart")))
    event_status.save_status()
    restarted_event_status = restart()

    restarted_event_status.new_event(new_event(ec.Event(text="after restart")))

    assert [event["id"] for event in restarted_event_status.events()] == [1, 2]


def test_rule_hits_are_restored_after_a_restart(
    event_status: EventStatus, restart: _Restart
) -> None:
    event_status.count_rule_match("disk")
    event_status.save_status()

    restarted_event_status = restart()

    assert list(restarted_event_status.get_rule_stats()) == [("disk", 1)]


def test_restored_events_count_towards_the_event_limits(
    event_status: EventStatus, restart: _Restart
) -> None:
    event = new_event(ec.Event(text="disk full"))
    event_status.new_event(event)
    event_status.save_status()

    restarted_event_status = restart()

    assert restarted_event_status.get_num_existing_events_by("by_host", event) == 1


def test_restored_events_of_old_versions_get_default_values(
    settings: ec.Settings, restart: _Restart
) -> None:
    _save_status_of_old_version(settings, [{"id": 1, "rule_id": "disk", "text": "disk full"}])

    restarted_event_status = restart()

    assert restarted_event_status.events() == [
        {
            "id": 1,
            "rule_id": "disk",
            "text": "disk full",
            "ipaddress": "",
            "host": "",
            "application": "",
            "pid": 0,
            "core_host": None,
            "host_in_downtime": False,
        }
    ]


def test_restored_events_of_old_versions_get_their_host_in_the_core(
    settings: ec.Settings, core_connection: FakeConnection, restart: _Restart
) -> None:
    core_connection.hosts = [new_host("fileserver")]
    _save_status_of_old_version(settings, [{"id": 1, "rule_id": "disk", "host": "FileServer"}])

    restarted_event_status = restart()

    assert [event["core_host"] for event in restarted_event_status.events()] == ["fileserver"]


def test_corrupt_saved_status_is_not_silently_discarded(
    settings: ec.Settings, restart: _Restart
) -> None:
    settings.paths.status_file.value.write_text("{")

    with pytest.raises(SyntaxError):
        restart()


# fmt: off
@pytest.mark.parametrize(
    "interval, timestamp, interval_count, expected",
    [
        pytest.param(3600,       7300.0,  0,   7200, id="start of the current hour"),
        pytest.param(3600,       7300.0,  1,  10800, id="start of the next hour"),
        pytest.param(3600,       7300.0, -1,   3600, id="start of the previous hour"),
        pytest.param((86400, 2), 10800.0, 0,   7200, id="start of the current day beginning at 2am"),
        pytest.param((86400, 2),  3600.0, 0, -79200, id="1am belongs to the previous day beginning at 2am"),
    ],
)
# fmt: on
def test_timestamps_are_clamped_to_the_start_of_their_interval(
    interval: ExpectInterval, timestamp: float, interval_count: int, expected: int
) -> None:
    assert EventStatus.clamp_timestamp_to_interval(interval, timestamp, interval_count) == expected

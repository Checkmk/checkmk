#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Limits for the number of open events"""

import pytest

import cmk.ec.export as ec
from cmk.ec.config import Config
from cmk.ec.event import LimitKind
from cmk.ec.main import EventServer, EventStatus

from .helpers import new_rule, process_message, RecordingHistory


@pytest.fixture(name="history")
def fixture_history() -> RecordingHistory:
    return RecordingHistory()


_LIMIT_KINDS = [
    pytest.param("overall", id="overall limit"),
    pytest.param("by_host", id="host limit"),
    pytest.param("by_rule", id="rule limit"),
]


def _only_limit(kind: LimitKind, limit: ec.EventLimit) -> ec.EventLimits:
    unlimited = ec.EventLimit(action="stop", limit=1000)
    return ec.EventLimits(
        overall=limit if kind == "overall" else unlimited,
        by_host=limit if kind == "by_host" else unlimited,
        by_rule=limit if kind == "by_rule" else unlimited,
    )


def _configure(
    event_server: EventServer,
    config: Config,
    history: RecordingHistory,
    event_limits: ec.EventLimits,
) -> None:
    event_server.reload_configuration(
        config
        | {"event_limit": event_limits, "rule_packs": [ec.default_rule_pack([new_rule({})])]},
        history,
    )


def _process_messages(event_server: EventServer, *texts: str) -> None:
    for text in texts:
        process_message(event_server, ec.Event(text=text))


def _texts_of_events(event_status: EventStatus) -> list[str]:
    return [
        "<overflow>" if "overflowed_limit" in event else event["text"]
        for event in event_status.events()
    ]


@pytest.mark.parametrize("kind", _LIMIT_KINDS)
def test_reached_limit_creates_an_overflow_event(
    event_server: EventServer,
    event_status: EventStatus,
    config: Config,
    history: RecordingHistory,
    kind: LimitKind,
) -> None:
    _configure(
        event_server,
        config,
        history,
        _only_limit(kind, ec.EventLimit(action="stop_overflow", limit=2)),
    )

    _process_messages(event_server, "1st", "2nd", "3rd", "4th")

    assert _texts_of_events(event_status) == ["1st", "<overflow>", "2nd"]


@pytest.mark.parametrize("kind", _LIMIT_KINDS)
def test_reaching_the_limit_again_creates_no_further_overflow_event_while_one_is_open(
    event_server: EventServer,
    event_status: EventStatus,
    config: Config,
    history: RecordingHistory,
    kind: LimitKind,
) -> None:
    _configure(
        event_server,
        config,
        history,
        _only_limit(kind, ec.EventLimit(action="stop_overflow", limit=2)),
    )
    _process_messages(event_server, "1st", "2nd")
    for event in [e for e in event_status.events() if e["text"] in {"1st", "2nd"}]:
        event_status.remove_event(event, "DELETE")

    _process_messages(event_server, "3rd")

    assert _texts_of_events(event_status) == ["<overflow>", "3rd"]


def test_message_cannot_pose_as_an_open_overflow_event(
    event_server: EventServer, event_status: EventStatus, config: Config, history: RecordingHistory
) -> None:
    _configure(
        event_server,
        config,
        history,
        _only_limit("overall", ec.EventLimit(action="stop_overflow", limit=2)),
    )
    # A message tries to mark its event as an overflow event via structured data.
    message = (
        b"<134>1 2026-10-23T10:00:00Z fileserver smartd - - "
        b'[Checkmk@18662 overflowed_limit="overall"] 1st'
    )
    event_server.process_syslog_messages([message], None)

    _process_messages(event_server, "2nd")

    assert _texts_of_events(event_status) == ["1st", "<overflow>", "2nd"]

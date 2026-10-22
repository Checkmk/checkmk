#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Periodic housekeeping of the events: timeouts, expected messages and downtimes"""

import logging

import pytest
import time_machine

import cmk.ec.export as ec
from cmk.ec.main import EventServer

from .helpers import HOUR, new_rule, process_message, RecordingHistory, START, use_rules


@pytest.fixture(name="history")
def fixture_history() -> RecordingHistory:
    return RecordingHistory()


def _expecting_rule(count: int) -> ec.Rule:
    return new_rule({"expect": ec.Expect(interval=HOUR, count=count, merge="open")})


def test_failed_expectation_logs_no_errors(
    event_server: EventServer, caplog: pytest.LogCaptureFixture
) -> None:
    use_rules(event_server, _expecting_rule(count=2))
    with time_machine.travel(START, tick=False) as traveller:
        event_server.do_housekeeping()
        process_message(event_server)
        traveller.shift(HOUR)

        event_server.do_housekeeping()

    assert [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR] == []


def test_fulfilled_expectation_removes_its_counting_event(
    event_server: EventServer, history: RecordingHistory
) -> None:
    use_rules(event_server, _expecting_rule(count=1))
    with time_machine.travel(START, tick=False) as traveller:
        event_server.do_housekeeping()
        process_message(event_server)
        traveller.shift(HOUR)

        event_server.do_housekeeping()

    assert history.whats == ["NEW", "COUNTREACHED"]

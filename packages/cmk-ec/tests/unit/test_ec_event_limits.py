#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Limits for the number of open events"""

import logging
import time

import pytest
import time_machine

import cmk.ec.export as ec
from cmk.ccc.hostaddress import HostName
from cmk.ec.config import Config
from cmk.ec.event import LimitKind
from cmk.ec.main import EventServer, EventStatus, StatusServer

from .helpers import (
    FakeConnection,
    HOUR,
    INTERVAL_START,
    new_count,
    new_event,
    new_host,
    new_rule,
    process_message,
    query_status_server,
    RecordingHistory,
    START,
)


@pytest.fixture(name="history")
def fixture_history() -> RecordingHistory:
    return RecordingHistory()


_LIMIT_KINDS = [
    pytest.param("overall", id="overall limit"),
    pytest.param("by_host", id="host limit"),
    pytest.param("by_rule", id="rule limit"),
]


_UNLIMITED = ec.EventLimit(action="stop", limit=1000)
_NO_LIMITS = ec.EventLimits(overall=_UNLIMITED, by_host=_UNLIMITED, by_rule=_UNLIMITED)


def _only_limit(kind: LimitKind, limit: ec.EventLimit) -> ec.EventLimits:
    return ec.EventLimits(
        overall=limit if kind == "overall" else _UNLIMITED,
        by_host=limit if kind == "by_host" else _UNLIMITED,
        by_rule=limit if kind == "by_rule" else _UNLIMITED,
    )


def _configure(
    event_server: EventServer,
    config: Config,
    history: RecordingHistory,
    event_limits: ec.EventLimits,
    rule: ec.Rule | None = None,
) -> None:
    rule_packs = [ec.default_rule_pack([new_rule({}) if rule is None else rule])]
    event_server.reload_configuration(
        config | {"event_limit": event_limits, "rule_packs": rule_packs}, history
    )


def _process_messages(event_server: EventServer, *texts: str) -> None:
    for text in texts:
        process_message(event_server, ec.Event(text=text))


def _status(event_server: EventServer) -> dict[str, object]:
    [row] = event_server.get_status()
    return dict(zip((name for name, _default in EventServer.status_columns()), row, strict=True))


def _texts_of_events(event_status: EventStatus) -> list[str]:
    return [
        "<overflow>" if "overflowed_limit" in event else event["text"]
        for event in event_status.events()
    ]


@pytest.mark.parametrize("kind", _LIMIT_KINDS)
def test_reached_limit_stops_creating_events(
    event_server: EventServer,
    event_status: EventStatus,
    config: Config,
    history: RecordingHistory,
    kind: LimitKind,
) -> None:
    _configure(
        event_server, config, history, _only_limit(kind, ec.EventLimit(action="stop", limit=2))
    )

    _process_messages(event_server, "1st", "2nd", "3rd", "4th")

    assert _texts_of_events(event_status) == ["1st", "2nd"]


def test_counting_rule_does_not_open_an_event_dropped_by_a_reached_limit(
    event_server: EventServer, config: Config, history: RecordingHistory
) -> None:
    # Each disk gets an event of its own, which its first message opens.
    count = new_count(1, period=60) | {"separate_match_groups": True}
    rule = new_rule({"match": r"disk (\S+) failed", "count": count})
    _configure(
        event_server,
        config,
        history,
        _only_limit("by_rule", ec.EventLimit(action="stop", limit=1)),
        rule,
    )

    _process_messages(event_server, "disk sda failed", "disk sdb failed")

    assert history.whats == ["NEW", "COUNTREACHED"]


@pytest.mark.parametrize("kind", _LIMIT_KINDS)
def test_reached_limit_deletes_the_oldest_events(
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
        _only_limit(kind, ec.EventLimit(action="delete_oldest", limit=2)),
    )

    _process_messages(event_server, "1st", "2nd", "3rd", "4th")

    assert _texts_of_events(event_status) == ["3rd", "4th"]


def test_limit_does_not_delete_events_for_an_event_which_a_further_limit_drops(
    event_server: EventServer, event_status: EventStatus, config: Config, history: RecordingHistory
) -> None:
    event_status.new_event(new_event(ec.Event(text="of another rule")))
    event_limits = ec.EventLimits(
        overall=ec.EventLimit(action="delete_oldest", limit=2),
        by_host=ec.EventLimit(action="stop", limit=1000),
        by_rule=ec.EventLimit(action="stop", limit=1),
    )
    _configure(event_server, config, history, event_limits)
    _process_messages(event_server, "1st")

    # The overall limit would delete the oldest event, but the rule limit drops the message.
    _process_messages(event_server, "2nd")

    assert _texts_of_events(event_status) == ["of another rule", "1st"]


def test_deleting_events_for_one_limit_can_keep_the_event_from_reaching_another_one(
    event_server: EventServer, event_status: EventStatus, config: Config, history: RecordingHistory
) -> None:
    event_status.new_event(new_event(ec.Event(text="of another rule")))
    # The rule keeps only its newest event.
    rule = new_rule({"event_limit": ec.EventLimit(action="delete_oldest", limit=1)})
    _configure(
        event_server,
        config,
        history,
        _only_limit("overall", ec.EventLimit(action="stop_overflow", limit=3)),
        rule,
    )
    _process_messages(event_server, "1st")

    # The overall limit would be reached, but the rule limit deletes the 1st event first.
    _process_messages(event_server, "2nd")

    assert _texts_of_events(event_status) == ["of another rule", "2nd"]


def test_limit_deleting_the_oldest_events_makes_room_for_overflow_events_of_other_limits(
    event_server: EventServer, event_status: EventStatus, config: Config, history: RecordingHistory
) -> None:
    event_status.new_event(new_event(ec.Event(text="of another rule")))
    event_limits = ec.EventLimits(
        overall=ec.EventLimit(action="delete_oldest", limit=3),
        by_host=ec.EventLimit(action="stop", limit=1000),
        by_rule=ec.EventLimit(action="stop_overflow", limit=2),
    )
    _configure(event_server, config, history, event_limits)
    _process_messages(event_server, "1st")

    # The rule limit creates an overflow event, which counts towards the overall limit, too.
    _process_messages(event_server, "2nd")

    assert _texts_of_events(event_status) == ["1st", "<overflow>", "2nd"]


def test_limit_deleting_the_oldest_events_does_not_delete_an_overflow_event_just_created(
    event_server: EventServer, event_status: EventStatus, config: Config, history: RecordingHistory
) -> None:
    event_limits = ec.EventLimits(
        overall=ec.EventLimit(action="delete_oldest", limit=1),
        by_host=ec.EventLimit(action="stop", limit=1000),
        by_rule=ec.EventLimit(action="stop_overflow", limit=1),
    )
    _configure(event_server, config, history, event_limits)

    # The rule limit creates an overflow event, for which the overall limit can't make room.
    _process_messages(event_server, "1st")

    assert _texts_of_events(event_status) == ["<overflow>", "1st"]


def test_deleting_the_oldest_events_keeps_the_newest_one_even_with_a_zero_limit(
    event_server: EventServer, event_status: EventStatus, config: Config, history: RecordingHistory
) -> None:
    # Nobody validates settings written by hand.
    _configure(
        event_server,
        config,
        history,
        _only_limit("overall", ec.EventLimit(action="delete_oldest", limit=0)),
    )

    _process_messages(event_server, "1st", "2nd")

    assert _texts_of_events(event_status) == ["2nd"]


def test_reached_host_limit_deletes_the_oldest_events_counted_towards_it(
    event_server: EventServer,
    event_status: EventStatus,
    config: Config,
    history: RecordingHistory,
    core_connection: FakeConnection,
) -> None:
    # The host's events from before it was in the core are counted separately.
    event_status.new_event(new_event(ec.Event(text="before the core knew the host")))
    core_connection.hosts = [new_host("test-host")]
    _configure(
        event_server,
        config,
        history,
        _only_limit("by_host", ec.EventLimit(action="delete_oldest", limit=2)),
    )

    _process_messages(event_server, "1st", "2nd", "3rd")

    assert _texts_of_events(event_status) == ["before the core knew the host", "2nd", "3rd"]


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


@pytest.mark.parametrize("kind", _LIMIT_KINDS)
def test_archiving_only_the_overflow_event_keeps_dropping_messages(
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
    [overflow_event] = [event for event in event_status.events() if "overflowed_limit" in event]
    event_status.remove_event(overflow_event, "DELETE")

    _process_messages(event_server, "3rd")

    assert _texts_of_events(event_status) == ["1st", "2nd"]


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


def test_messages_are_not_counted_into_the_overflow_event_of_their_rule(
    event_server: EventServer, event_status: EventStatus, config: Config, history: RecordingHistory
) -> None:
    # All messages count up the same event, which the second one opens.
    _configure(
        event_server,
        config,
        history,
        _only_limit("by_rule", ec.EventLimit(action="stop_overflow", limit=1)),
        new_rule({"count": new_count(2, period=60)}),
    )
    _process_messages(event_server, "1st")

    _process_messages(event_server, "2nd")

    assert [(event["phase"], event["count"]) for event in event_status.events()] == [
        ("open", 1),
        ("open", 2),
    ]


def test_missing_expected_messages_are_not_merged_into_the_overflow_event_of_their_rule(
    event_server: EventServer, event_status: EventStatus, config: Config, history: RecordingHistory
) -> None:
    event_limits = _only_limit("by_rule", ec.EventLimit(action="stop_overflow", limit=1))
    _configure(event_server, config, history, event_limits)
    _process_messages(event_server, "1st")
    [event] = [event for event in event_status.events() if "overflowed_limit" not in event]
    event_status.remove_event(event, "DELETE")
    # The rule expects messages now, so an event about a missing one is merged into an open one.
    expecting_rule = new_rule({"expect": ec.Expect(interval=3600, count=1, merge="open")})
    _configure(event_server, config, history, event_limits, expecting_rule)
    with time_machine.travel(1_700_000_000.0, tick=False) as traveller:
        event_server.do_housekeeping()
        traveller.shift(3600)

        event_server.do_housekeeping()

    assert [event["count"] for event in event_status.events()] == [1, 1]


def test_cancelling_message_does_not_cancel_the_overflow_event_of_its_rule(
    event_server: EventServer, event_status: EventStatus, config: Config, history: RecordingHistory
) -> None:
    # The overflow event has neither a host name nor match groups, and the rule doesn't compare the
    # application when cancelling, so only the rule ID tells the overflow event apart.
    rule = new_rule(
        {
            "match": "disk failed",
            "match_ok": "disk ok",
            "match_application": "smartd",
            "cancel_application": "smartd",
        }
    )
    event_limits = _only_limit("by_rule", ec.EventLimit(action="stop_overflow", limit=1))
    _configure(event_server, config, history, event_limits, rule)
    process_message(event_server, ec.Event(text="disk failed", application="smartd"))

    process_message(event_server, ec.Event(text="disk ok", host=HostName(""), application="smartd"))

    assert _texts_of_events(event_status) == ["<overflow>", "disk failed"]


def test_messages_are_not_counted_into_an_overflow_event_of_an_older_version(
    event_server: EventServer, event_status: EventStatus, config: Config, history: RecordingHistory
) -> None:
    # Older versions didn't mark overflow events.
    event_status.new_event(
        new_event(
            ec.Event(
                rule_id="rule",
                application="Event Console",
                text='The rule event limit of 1 open events has been reached for rule "rule". '
                "Not opening any additional event for this rule until open events have been "
                "archived.",
            )
        )
    )
    # All messages count up the same event, which the second one opens.
    rule = new_rule({"count": new_count(2, period=60)})
    _configure(event_server, config, history, _NO_LIMITS, rule)

    _process_messages(event_server, "1st", "2nd")

    assert [(event["phase"], event["count"]) for event in event_status.events()] == [
        ("open", 1),
        ("open", 2),
    ]


def test_limit_does_not_act_on_an_event_which_a_further_limit_drops(
    event_server: EventServer, event_status: EventStatus, config: Config, history: RecordingHistory
) -> None:
    event_limits = ec.EventLimits(
        overall=ec.EventLimit(action="stop_overflow", limit=2),
        by_host=ec.EventLimit(action="stop", limit=1),
        by_rule=ec.EventLimit(action="stop", limit=1000),
    )
    _configure(event_server, config, history, event_limits)
    _process_messages(event_server, "1st")

    # The overall limit would be reached, but the host limit drops the message.
    _process_messages(event_server, "2nd")

    assert _texts_of_events(event_status) == ["1st"]


def test_limit_of_a_rule_overrides_the_general_rule_limit(
    event_server: EventServer, event_status: EventStatus, config: Config, history: RecordingHistory
) -> None:
    rule = new_rule({"event_limit": ec.EventLimit(action="stop", limit=1)})
    _configure(event_server, config, history, _NO_LIMITS, rule)

    _process_messages(event_server, "1st", "2nd")

    assert _texts_of_events(event_status) == ["1st"]


def test_limit_of_a_host_overrides_the_general_host_limit(
    event_server: EventServer,
    event_status: EventStatus,
    config: Config,
    history: RecordingHistory,
    core_connection: FakeConnection,
) -> None:
    core_connection.hosts = [new_host("test-host", custom_variables={"EC_EVENT_LIMIT": "1:stop"})]
    _configure(event_server, config, history, _NO_LIMITS)

    _process_messages(event_server, "1st", "2nd")

    assert _texts_of_events(event_status) == ["1st"]


def test_status_shows_the_reached_limits(
    event_server: EventServer, config: Config, history: RecordingHistory
) -> None:
    one_event = ec.EventLimit(action="stop", limit=1)
    _configure(
        event_server,
        config,
        history,
        ec.EventLimits(overall=one_event, by_host=one_event, by_rule=one_event),
        new_rule({"id": "disk"}),
    )

    _process_messages(event_server, "disk full")

    assert {
        "status_event_limit_active_hosts": ["test-host"],
        "status_event_limit_active_rules": ["disk"],
        "status_event_limit_active_overall": True,
    }.items() <= _status(event_server).items()


def test_host_limit_stays_consistent_when_the_host_of_an_event_changes_unnoticed(
    event_server: EventServer, event_status: EventStatus, config: Config, history: RecordingHistory
) -> None:
    one_event = _only_limit("by_host", ec.EventLimit(action="stop", limit=1))
    _configure(event_server, config, history, one_event)
    _process_messages(event_server, "disk full")
    [event] = event_status.events()
    # Like a code path changing the host without telling the host limit
    event["host"] = HostName("nas")

    event_status.remove_event(event, "DELETE")

    assert _status(event_server)["status_event_limit_active_hosts"] == []


def test_host_limit_counts_a_counted_event_for_the_host_of_its_last_message(
    event_server: EventServer, config: Config, history: RecordingHistory
) -> None:
    # The messages of all hosts count up the same event, which gets the host of the last one.
    rule = new_rule({"count": new_count(3, period=HOUR)})
    one_event = _only_limit("by_host", ec.EventLimit(action="stop", limit=1))
    _configure(event_server, config, history, one_event, rule)
    process_message(event_server, ec.Event(host=HostName("fileserver"), text="disk full"))

    process_message(event_server, ec.Event(host=HostName("nas"), text="disk full"))

    assert _status(event_server)["status_event_limit_active_hosts"] == ["nas"]


def test_event_counted_for_several_hosts_can_be_deleted(
    event_server: EventServer,
    event_status: EventStatus,
    status_server: StatusServer,
    config: Config,
    history: RecordingHistory,
) -> None:
    _configure(event_server, config, history, _NO_LIMITS, new_rule({"count": new_count(3, HOUR)}))
    process_message(event_server, ec.Event(host=HostName("fileserver"), text="disk full"))
    process_message(event_server, ec.Event(host=HostName("nas"), text="disk full"))

    query_status_server(status_server, "COMMAND DELETE;1;harry")

    assert event_status.events() == []


def test_host_limit_counts_a_merged_event_about_missing_messages_for_its_rewritten_host(
    event_server: EventServer, config: Config, history: RecordingHistory
) -> None:
    expect = ec.Expect(interval=HOUR, count=1, merge="open")
    one_event = _only_limit("by_host", ec.EventLimit(action="stop", limit=1))
    _configure(
        event_server,
        config,
        history,
        one_event,
        new_rule({"expect": expect, "set_host": "backup-server"}),
    )
    with time_machine.travel(START, tick=False) as traveller:
        event_server.do_housekeeping()
        traveller.shift(HOUR)
        event_server.do_housekeeping()
        # The rule changes after opening an event about the missing message.
        _configure(
            event_server,
            config,
            history,
            one_event,
            new_rule({"expect": expect, "set_host": "backup-host"}),
        )
        traveller.shift(HOUR)

        event_server.do_housekeeping()

    assert _status(event_server)["status_event_limit_active_hosts"] == ["backup-host"]


def test_expected_message_counts_although_the_limit_of_its_rule_is_reached(
    event_server: EventServer, event_status: EventStatus, config: Config, history: RecordingHistory
) -> None:
    rule = new_rule(
        {
            "expect": ec.Expect(interval=HOUR, count=1, merge="open"),
            "event_limit": ec.EventLimit(action="stop", limit=1),
        }
    )
    _configure(event_server, config, history, _NO_LIMITS, rule)
    with time_machine.travel(START, tick=False) as traveller:
        event_server.do_housekeeping()
        traveller.shift(HOUR)
        # The event about the missing message reaches the limit of the rule.
        event_server.do_housekeeping()
        _process_messages(event_server, "backup done")
        traveller.shift(HOUR)

        event_server.do_housekeeping()

    assert [event["count"] for event in event_status.events()] == [1]


def test_counting_event_of_an_expecting_rule_reaching_a_limit_creates_an_overflow_event(
    event_server: EventServer, event_status: EventStatus, config: Config, history: RecordingHistory
) -> None:
    rule = new_rule({"expect": ec.Expect(interval=HOUR, count=2, merge="open")})
    event_limits = _only_limit("overall", ec.EventLimit(action="stop_overflow", limit=1))
    _configure(event_server, config, history, event_limits, rule)

    _process_messages(event_server, "backup done")

    assert _texts_of_events(event_status) == ["<overflow>", "backup done"]


def test_event_about_a_missing_message_reaching_a_limit_creates_an_overflow_event(
    event_server: EventServer, event_status: EventStatus, config: Config, history: RecordingHistory
) -> None:
    rule = new_rule({"expect": ec.Expect(interval=HOUR, count=1, merge="open")})
    event_limits = _only_limit("overall", ec.EventLimit(action="stop_overflow", limit=1))
    _configure(event_server, config, history, event_limits, rule)
    with time_machine.travel(START, tick=False) as traveller:
        event_server.do_housekeeping()
        traveller.shift(HOUR)

        event_server.do_housekeeping()

    interval_start = time.strftime("%F %T", time.localtime(INTERVAL_START))
    assert _texts_of_events(event_status) == [
        "<overflow>",
        f"Expected message did not arrive since {interval_start}",
    ]


def test_failed_expectation_logs_no_errors_with_a_limit_deleting_the_oldest_events(
    event_server: EventServer,
    config: Config,
    history: RecordingHistory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # The rule keeps only its newest event.
    rule = new_rule(
        {
            "expect": ec.Expect(interval=HOUR, count=2, merge="open"),
            "event_limit": ec.EventLimit(action="delete_oldest", limit=1),
        }
    )
    _configure(event_server, config, history, _NO_LIMITS, rule)
    with time_machine.travel(START, tick=False) as traveller:
        event_server.do_housekeeping()
        _process_messages(event_server, "backup done")
        traveller.shift(HOUR)

        event_server.do_housekeeping()

    assert [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR] == []


def test_counting_event_of_a_failed_expectation_takes_up_no_room_within_the_limits(
    event_server: EventServer, event_status: EventStatus, config: Config, history: RecordingHistory
) -> None:
    # The rule keeps its two newest events, and it opens a new one for each failed expectation.
    rule = new_rule(
        {
            "expect": ec.Expect(interval=HOUR, count=2, merge="never"),
            "event_limit": ec.EventLimit(action="delete_oldest", limit=2),
        }
    )
    _configure(event_server, config, history, _NO_LIMITS, rule)
    with time_machine.travel(START, tick=False) as traveller:
        event_server.do_housekeeping()
        traveller.shift(HOUR)
        # No expected message arrives in the first interval, one in the second one.
        event_server.do_housekeeping()
        _process_messages(event_server, "backup done")
        traveller.shift(HOUR)

        event_server.do_housekeeping()

    first_interval_start = time.strftime("%F %T", time.localtime(INTERVAL_START))
    second_interval_start = time.strftime("%F %T", time.localtime(INTERVAL_START + HOUR))
    assert _texts_of_events(event_status) == [
        f"Expected message did not arrive since {first_interval_start}",
        f"Expected message arrived only 1 out of 2 times since {second_interval_start}",
    ]

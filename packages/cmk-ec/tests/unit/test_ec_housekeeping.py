#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Periodic housekeeping of the events: timeouts, expected messages and downtimes"""

import logging
import signal
import time
from collections.abc import Iterator, Sequence
from typing import Literal

import pytest
import time_machine

import cmk.ec.export as ec
from cmk.ccc.hostaddress import HostName
from cmk.ec.config import Config, ScriptAction, ScriptActionConfig
from cmk.ec.event import EventPhase
from cmk.ec.history import HistoryWhat
from cmk.ec.main import (
    EventServer,
    EventStatus,
    MKSignalException,
    SignalHandler,
    StatusServer,
)

from .helpers import (
    FakeConnection,
    HOUR,
    INTERVAL_START,
    new_count,
    new_host,
    new_rule,
    process_message,
    query_status_server,
    RecordingHistory,
    START,
    use_rules,
)


@pytest.fixture(name="history")
def fixture_history() -> RecordingHistory:
    return RecordingHistory()


def _phases(event_status: EventStatus) -> list[EventPhase]:
    return [event["phase"] for event in event_status.events()]


def _counting_rule(
    count: int, period: int, algorithm: Literal["interval", "tokenbucket", "dynabucket"]
) -> ec.Rule:
    return new_rule({"count": new_count(count, period) | {"algorithm": algorithm}})


def _expecting_rule(count: int, merge: Literal["open", "acked", "never"] = "open") -> ec.Rule:
    return new_rule({"expect": ec.Expect(interval=HOUR, count=count, merge=merge)})


@pytest.mark.parametrize(
    "changed_rules, expected_reason",
    [
        pytest.param([], "ORPHANED", id="rule deleted"),
        pytest.param([new_rule({})], "NOCOUNT", id="rule no longer counts"),
    ],
)
def test_counting_event_is_removed_when_its_rule_no_longer_counts(
    event_server: EventServer,
    history: RecordingHistory,
    changed_rules: Sequence[ec.Rule],
    expected_reason: HistoryWhat,
) -> None:
    use_rules(event_server, new_rule({"count": new_count(2, period=HOUR)}))
    process_message(event_server)
    use_rules(event_server, *changed_rules)

    event_server.do_housekeeping()

    assert history.whats == ["NEW", expected_reason]


def test_counting_event_is_removed_at_the_end_of_its_period(
    event_server: EventServer, history: RecordingHistory
) -> None:
    use_rules(event_server, _counting_rule(count=2, period=60, algorithm="interval"))
    with time_machine.travel(START, tick=False) as traveller:
        process_message(event_server)

        traveller.shift(59)
        event_server.do_housekeeping()
        assert history.whats == ["NEW"]

        traveller.shift(1)
        event_server.do_housekeeping()
        assert history.whats == ["NEW", "COUNTFAILED"]


@pytest.mark.parametrize(
    "algorithm, expected_count",
    [
        # 3 messages per minute => a new token every 20 seconds
        pytest.param("tokenbucket", 1, id="token bucket"),
        # ... but with only 2 messages counted so far => a new token every 30 seconds
        pytest.param("dynabucket", 2, id="dynamic token bucket"),
    ],
)
def test_token_buckets_refill_at_their_rate(
    event_server: EventServer,
    event_status: EventStatus,
    algorithm: Literal["tokenbucket", "dynabucket"],
    expected_count: int,
) -> None:
    use_rules(event_server, _counting_rule(count=3, period=60, algorithm=algorithm))
    with time_machine.travel(START, tick=False) as traveller:
        process_message(event_server)
        process_message(event_server)
        traveller.shift(20)

        event_server.do_housekeeping()

    assert [event["count"] for event in event_status.events()] == [expected_count]


def test_counting_event_is_removed_when_its_token_bucket_is_full_again(
    event_server: EventServer, history: RecordingHistory
) -> None:
    use_rules(event_server, _counting_rule(count=3, period=60, algorithm="tokenbucket"))
    with time_machine.travel(START, tick=False) as traveller:
        process_message(event_server)
        traveller.shift(20)

        event_server.do_housekeeping()

    assert history.whats == ["NEW", "COUNTFAILED"]


def test_delayed_event_opens_when_its_delay_is_over(
    event_server: EventServer, event_status: EventStatus
) -> None:
    use_rules(event_server, new_rule({"delay": 60}))
    with time_machine.travel(START, tick=False) as traveller:
        process_message(event_server)

        traveller.shift(59)
        event_server.do_housekeeping()
        assert _phases(event_status) == ["delayed"]

        traveller.shift(1)
        event_server.do_housekeeping()
        assert _phases(event_status) == ["open"]


def test_delayed_event_of_an_autodeleting_rule_is_closed_when_its_delay_is_over(
    event_server: EventServer, history: RecordingHistory
) -> None:
    use_rules(event_server, new_rule({"delay": 60, "autodelete": True}))
    with time_machine.travel(START, tick=False) as traveller:
        process_message(event_server)
        traveller.shift(60)

        event_server.do_housekeeping()

    assert history.whats == ["NEW", "DELAYOVER", "AUTODELETE"]


def test_delayed_event_of_a_deleted_rule_opens_nevertheless(
    event_server: EventServer, event_status: EventStatus
) -> None:
    use_rules(event_server, new_rule({"delay": 60}))
    with time_machine.travel(START, tick=False) as traveller:
        process_message(event_server)
        use_rules(event_server)
        traveller.shift(60)

        event_server.do_housekeeping()

    assert _phases(event_status) == ["open"]


@pytest.mark.parametrize(
    "acknowledged, expected_phases",
    [
        pytest.param("0", [], id="open event expires"),
        pytest.param("1", ["ack"], id="acknowledged event lives on"),
    ],
)
def test_event_expires_after_its_lifetime_only_in_the_configured_phases(
    event_server: EventServer,
    event_status: EventStatus,
    status_server: StatusServer,
    acknowledged: str,
    expected_phases: list[EventPhase],
) -> None:
    use_rules(event_server, new_rule({"livetime": (60, ["open"])}))
    with time_machine.travel(START, tick=False) as traveller:
        process_message(event_server)
        query_status_server(status_server, f"COMMAND UPDATE;1;harry;{acknowledged};;")
        traveller.shift(60)

        event_server.do_housekeeping()

    assert _phases(event_status) == expected_phases


def test_missing_expected_message_opens_an_event_since_the_start_of_the_interval(
    event_server: EventServer, event_status: EventStatus
) -> None:
    use_rules(event_server, _expecting_rule(count=1))
    with time_machine.travel(START, tick=False) as traveller:
        event_server.do_housekeeping()
        traveller.shift(HOUR)

        event_server.do_housekeeping()

    interval_start = time.strftime("%F %T", time.localtime(INTERVAL_START))
    [event] = event_status.events()
    assert event["text"] == f"Expected message did not arrive since {interval_start}"


def test_too_few_expected_messages_open_an_event_since_the_start_of_the_interval(
    event_server: EventServer, event_status: EventStatus
) -> None:
    use_rules(event_server, _expecting_rule(count=2))
    with time_machine.travel(START, tick=False) as traveller:
        event_server.do_housekeeping()
        traveller.shift(600)
        process_message(event_server)
        traveller.shift(HOUR)

        event_server.do_housekeeping()

    interval_start = time.strftime("%F %T", time.localtime(INTERVAL_START))
    [event] = event_status.events()
    assert event["text"] == f"Expected message arrived only 1 out of 2 times since {interval_start}"


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


@pytest.mark.parametrize(
    "merge, expected_counts",
    [
        pytest.param("open", [2], id="merging into the open event"),
        pytest.param("never", [1, 1], id="never merging"),
    ],
)
def test_missing_expected_messages_are_merged_as_configured(
    event_server: EventServer,
    event_status: EventStatus,
    merge: Literal["open", "never"],
    expected_counts: list[int],
) -> None:
    use_rules(event_server, _expecting_rule(count=1, merge=merge))
    with time_machine.travel(START, tick=False) as traveller:
        event_server.do_housekeeping()
        traveller.shift(HOUR)
        event_server.do_housekeeping()
        traveller.shift(HOUR)

        event_server.do_housekeeping()

    assert [event["count"] for event in event_status.events()] == expected_counts


def test_expecting_rule_of_another_site_opens_no_event(
    event_server: EventServer, event_status: EventStatus
) -> None:
    rule = _expecting_rule(count=1)
    rule["match_site"] = ["other_site"]
    use_rules(event_server, rule)
    with time_machine.travel(START, tick=False) as traveller:
        event_server.do_housekeeping()
        traveller.shift(HOUR)

        event_server.do_housekeeping()

    assert event_status.events() == []


def test_expectation_intervals_missed_while_not_running_open_no_event(
    event_server: EventServer, event_status: EventStatus
) -> None:
    use_rules(event_server, _expecting_rule(count=1))
    with time_machine.travel(START, tick=False) as traveller:
        event_server.do_housekeeping()
        traveller.shift(3 * HOUR)

        event_server.do_housekeeping()

    assert event_status.events() == []


def test_event_created_in_downtime_is_removed_when_the_downtime_ends(
    event_server: EventServer, core_connection: FakeConnection, history: RecordingHistory
) -> None:
    core_connection.hosts = [new_host("test-host")]
    core_connection.hosts_in_downtime = {HostName("test-host")}
    use_rules(event_server, new_rule({}))
    process_message(event_server)

    event_server.do_housekeeping()
    assert history.whats == ["NEW"]

    core_connection.hosts_in_downtime = set()
    event_server.do_housekeeping()
    assert history.whats == ["NEW", "AUTODELETE"]


def test_all_events_created_in_downtime_are_removed_when_the_downtime_ends(
    event_server: EventServer, event_status: EventStatus, core_connection: FakeConnection
) -> None:
    core_connection.hosts = [new_host("test-host")]
    core_connection.hosts_in_downtime = {HostName("test-host")}
    use_rules(event_server, new_rule({}))
    for _ in range(3):
        process_message(event_server)
    core_connection.hosts_in_downtime = set()

    event_server.do_housekeeping()

    assert event_status.events() == []


def test_missing_expected_message_is_merged_into_an_event_from_before_the_rule_expected_it(
    event_server: EventServer, event_status: EventStatus
) -> None:
    use_rules(event_server, new_rule({}))
    process_message(event_server)
    use_rules(event_server, _expecting_rule(count=1))
    with time_machine.travel(START, tick=False) as traveller:
        event_server.do_housekeeping()
        traveller.shift(HOUR)

        event_server.do_housekeeping()

    assert [event.get("count", 1) for event in event_status.events()] == [2]


@pytest.fixture(name="signalling_action")
def fixture_signalling_action(
    event_server: EventServer, config: Config, history: RecordingHistory
) -> Iterator[str]:
    """Returns the ID of an action letting a signal arrive at the EC while the EC waits for it,
    like "omd stop" does"""
    action = ScriptAction(
        id="slow",
        title="A slow script",
        hidden=False,
        disabled=False,
        action=("script", ScriptActionConfig(script="kill -USR1 $PPID; exec sleep 10")),
    )
    event_server.reload_configuration(
        config | {"actions": [action], "action": {"slow": action}}, history
    )
    previous_handler = signal.signal(
        signal.SIGUSR1, SignalHandler(logging.getLogger("cmk.mkeventd"))
    )
    yield action["id"]
    signal.signal(signal.SIGUSR1, previous_handler)


def test_signal_while_running_an_action_is_passed_on(
    event_server: EventServer, signalling_action: str
) -> None:
    use_rules(event_server, new_rule({"delay": 60, "actions": [signalling_action]}))
    with time_machine.travel(START, tick=False) as traveller:
        process_message(event_server)
        # The delayed event opens now, running the action.
        traveller.shift(60)

        with pytest.raises(MKSignalException):
            event_server.do_housekeeping()


def test_events_closed_before_a_signal_interrupts_the_housekeeping_are_removed(
    event_server: EventServer, event_status: EventStatus, signalling_action: str
) -> None:
    use_rules(
        event_server,
        new_rule({"id": "expiring", "match": "disk full", "livetime": (60, ["open"])}),
        new_rule(
            {"id": "delayed", "match": "backup failed", "delay": 60, "actions": [signalling_action]}
        ),
    )
    with time_machine.travel(START, tick=False) as traveller:
        process_message(event_server, ec.Event(text="disk full"))
        process_message(event_server, ec.Event(text="backup failed"))
        # The 1st event expires now, before the delayed 2nd one opens, running the action.
        traveller.shift(60)

        with pytest.raises(MKSignalException):
            event_server.do_housekeeping()

    assert [event["rule_id"] for event in event_status.events()] == ["delayed"]


def test_interval_without_the_expected_message_is_checked_only_once_despite_a_signal(
    event_server: EventServer, event_status: EventStatus, signalling_action: str
) -> None:
    expect = ec.Expect(interval=HOUR, count=1, merge="never")
    use_rules(event_server, new_rule({"expect": expect, "actions": [signalling_action]}))
    with time_machine.travel(START, tick=False) as traveller:
        event_server.do_housekeeping()
        traveller.shift(HOUR)
        # The event about the missing message opens, running the action.
        with pytest.raises(MKSignalException):
            event_server.do_housekeeping()
        use_rules(event_server, new_rule({"expect": expect}))  # without the action

        event_server.do_housekeeping()

    interval_start = time.strftime("%F %T", time.localtime(INTERVAL_START))
    assert [event["text"] for event in event_status.events()] == [
        f"Expected message did not arrive since {interval_start}"
    ]


def test_autodeleting_rule_deletes_its_delayed_event_despite_a_signal(
    event_server: EventServer, event_status: EventStatus, signalling_action: str
) -> None:
    rule = new_rule({"delay": 60, "autodelete": True, "actions": [signalling_action]})
    use_rules(event_server, rule)
    with time_machine.travel(START, tick=False) as traveller:
        process_message(event_server)
        # The delayed event opens now, running the action.
        traveller.shift(60)

        with pytest.raises(MKSignalException):
            event_server.do_housekeeping()

    assert event_status.events() == []


def test_autodeleting_rule_deletes_its_event_about_a_missing_message_despite_a_signal(
    event_server: EventServer, event_status: EventStatus, signalling_action: str
) -> None:
    expect = ec.Expect(interval=HOUR, count=1, merge="open")
    use_rules(
        event_server,
        new_rule({"expect": expect, "autodelete": True, "actions": [signalling_action]}),
    )
    with time_machine.travel(START, tick=False) as traveller:
        event_server.do_housekeeping()
        # The event about the missing message opens now, running the action.
        traveller.shift(HOUR)

        with pytest.raises(MKSignalException):
            event_server.do_housekeeping()

    assert event_status.events() == []


@pytest.mark.parametrize(
    "rewriting, field",
    [
        pytest.param({"set_host": r"missing-\0"}, "host", id="host name"),
        pytest.param({"set_application": r"missing-\0"}, "application", id="application"),
    ],
)
def test_merged_event_about_missing_messages_is_rewritten_like_a_new_one(
    event_server: EventServer,
    event_status: EventStatus,
    rewriting: ec.Rule,
    field: Literal["host", "application"],
) -> None:
    rule = _expecting_rule(count=1)
    rule.update(rewriting)
    use_rules(event_server, rule)
    with time_machine.travel(START, tick=False) as traveller:
        event_server.do_housekeeping()
        traveller.shift(HOUR)
        event_server.do_housekeeping()
        traveller.shift(HOUR)

        event_server.do_housekeeping()

    assert [event[field] for event in event_status.events()] == ["missing-"]

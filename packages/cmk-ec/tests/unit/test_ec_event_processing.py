#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Turning incoming messages into events according to the rules"""

from typing import Literal

import pytest
import time_machine

import cmk.ec.export as ec
from cmk.ccc.hostaddress import HostName
from cmk.ec.config import Config
from cmk.ec.main import EventServer, EventStatus, SlaveStatus, StatusServer

from .helpers import (
    FakeConnection,
    HOUR,
    new_count,
    new_host,
    new_rule,
    process_message,
    query_status_server,
    RecordingHistory,
    replication_slave_config,
    START,
    use_rules,
)


@pytest.fixture(name="history")
def fixture_history() -> RecordingHistory:
    return RecordingHistory()


def _phases_and_counts(event_status: EventStatus) -> list[tuple[str, int]]:
    return [(event["phase"], event["count"]) for event in event_status.events()]


# fmt: off
@pytest.mark.parametrize(
    "rewriting, expected",
    [
        pytest.param({"set_text": r"Problem: \0"}, {"text": "Problem: disk full"}, id="text"),
        pytest.param({"set_comment": "see ticket"}, {"comment": "see ticket"}, id="comment"),
        pytest.param({"set_application": "storage"}, {"application": "storage"}, id="application"),
        pytest.param({"set_host": "nas"}, {"host": "nas", "orig_host": "fileserver"}, id="host"),
        pytest.param({"set_contact": "Harry Hirsch"}, {"contact": "Harry Hirsch"}, id="contact"),
    ],
)
# fmt: on
def test_rule_rewrites_the_event(
    event_server: EventServer, event_status: EventStatus, rewriting: ec.Rule, expected: ec.Event
) -> None:
    use_rules(event_server, new_rule(rewriting))

    process_message(event_server, ec.Event(text="disk full", host=HostName("fileserver")))

    assert expected.items() <= event_status.events()[0].items()


def test_rule_rewrites_the_event_with_the_matched_groups(
    event_server: EventServer, event_status: EventStatus
) -> None:
    use_rules(event_server, new_rule({"match": r"disk (\S+) full", "set_text": r"\1 is full"}))

    process_message(event_server, ec.Event(text="disk /var full"))

    assert [event["text"] for event in event_status.events()] == ["/var is full"]


@pytest.mark.parametrize(
    "precedence, expected_service_level",
    [
        pytest.param("message", 10, id="message takes precedence"),
        pytest.param("rule", 20, id="rule takes precedence"),
    ],
)
def test_event_gets_the_service_level_which_takes_precedence(
    event_server: EventServer,
    event_status: EventStatus,
    precedence: Literal["message", "rule"],
    expected_service_level: int,
) -> None:
    use_rules(event_server, new_rule({"sl": ec.ServiceLevel(value=20, precedence=precedence)}))

    process_message(event_server, ec.Event(sl=10))

    assert [event["sl"] for event in event_status.events()] == [expected_service_level]


def test_event_gets_the_contact_groups_of_its_rule(
    event_server: EventServer, event_status: EventStatus
) -> None:
    contact_groups = ec.ContactGroups(groups=["storage"], notify=True, precedence="rule")
    use_rules(event_server, new_rule({"contact_groups": contact_groups}))

    process_message(event_server, ec.Event(text="disk full"))

    assert (
        ec.Event(
            contact_groups=["storage"], contact_groups_notify=True, contact_groups_precedence="rule"
        ).items()
        <= event_status.events()[0].items()
    )


def test_event_gets_its_host_in_the_core(
    event_server: EventServer, event_status: EventStatus, core_connection: FakeConnection
) -> None:
    core_connection.hosts = [new_host("fileserver")]
    use_rules(event_server, new_rule({}))

    process_message(event_server, ec.Event(host=HostName("FileServer")))

    assert [event["core_host"] for event in event_status.events()] == ["fileserver"]


def test_event_of_host_in_downtime_is_marked(
    event_server: EventServer, event_status: EventStatus, core_connection: FakeConnection
) -> None:
    core_connection.hosts = [new_host("fileserver")]
    core_connection.hosts_in_downtime = {HostName("fileserver")}
    use_rules(event_server, new_rule({}))

    process_message(event_server, ec.Event(host=HostName("fileserver")))

    assert [event["host_in_downtime"] for event in event_status.events()] == [True]


def test_counting_event_opens_when_its_count_is_reached(
    event_server: EventServer, event_status: EventStatus
) -> None:
    use_rules(event_server, new_rule({"count": new_count(3, period=HOUR)}))

    process_message(event_server, ec.Event(text="disk full"))
    process_message(event_server, ec.Event(text="disk full"))
    assert _phases_and_counts(event_status) == [("counting", 2)]

    process_message(event_server, ec.Event(text="disk full"))
    assert _phases_and_counts(event_status) == [("open", 3)]


# fmt: off
@pytest.mark.parametrize(
    "separation, other_message",
    [
        pytest.param({"separate_host": True}, {"host": "nas"}, id="other host"),
        pytest.param({"separate_application": True}, {"application": "smartd"}, id="other application"),
        pytest.param({"separate_match_groups": True}, {"text": "disk /home full"}, id="other match groups"),
    ],
)
# fmt: on
def test_differing_messages_are_counted_separately(
    event_server: EventServer,
    event_status: EventStatus,
    separation: ec.Count,
    other_message: ec.Event,
) -> None:
    count = new_count(3, period=HOUR) | separation
    use_rules(event_server, new_rule({"match": r"disk (\S+) full", "count": count}))
    process_message(event_server, ec.Event(text="disk /var full"))

    process_message(event_server, ec.Event(text="disk /var full") | other_message)

    assert _phases_and_counts(event_status) == [("counting", 1), ("counting", 1)]


@pytest.mark.parametrize(
    "other_message",
    [
        pytest.param({"host": "nas"}, id="other host"),
        pytest.param({"application": "smartd"}, id="other application"),
        pytest.param({"text": "disk /home full"}, id="other match groups"),
    ],
)
def test_differing_messages_are_counted_together_by_default(
    event_server: EventServer, event_status: EventStatus, other_message: ec.Event
) -> None:
    count = new_count(3, period=HOUR)
    use_rules(event_server, new_rule({"match": r"disk (\S+) full", "count": count}))
    process_message(event_server, ec.Event(text="disk /var full"))

    process_message(event_server, ec.Event(text="disk /var full") | other_message)

    assert _phases_and_counts(event_status) == [("counting", 2)]


@pytest.mark.parametrize(
    "count_ack, expected_phases_and_counts",
    [
        pytest.param(False, [("ack", 1), ("open", 1)], id="not counting acknowledged events"),
        pytest.param(True, [("ack", 2)], id="counting acknowledged events"),
    ],
)
def test_messages_are_counted_for_acknowledged_events_only_if_configured(
    event_server: EventServer,
    event_status: EventStatus,
    status_server: StatusServer,
    count_ack: bool,
    expected_phases_and_counts: list[tuple[str, int]],
) -> None:
    count = new_count(1, period=HOUR) | {"count_ack": count_ack}
    use_rules(event_server, new_rule({"count": count}))
    process_message(event_server, ec.Event(text="disk full"))
    query_status_server(status_server, "COMMAND UPDATE;1;harry;1;;")

    process_message(event_server, ec.Event(text="disk full"))

    assert _phases_and_counts(event_status) == expected_phases_and_counts


def test_counting_starts_anew_after_the_count_duration(
    event_server: EventServer, event_status: EventStatus
) -> None:
    count = new_count(3, period=HOUR) | {"count_duration": 60}
    use_rules(event_server, new_rule({"count": count}))
    with time_machine.travel(START, tick=False) as traveller:
        process_message(event_server, ec.Event(text="disk full"))
        traveller.shift(61)

        process_message(event_server, ec.Event(text="disk full"))

    assert _phases_and_counts(event_status) == [("counting", 1), ("counting", 1)]


def test_messages_of_an_expecting_rule_are_counted(
    event_server: EventServer, event_status: EventStatus
) -> None:
    expect = ec.Expect(interval=HOUR, count=3, merge="open")
    use_rules(event_server, new_rule({"expect": expect}))

    process_message(event_server, ec.Event(text="backup done"))
    process_message(event_server, ec.Event(text="backup done"))

    assert _phases_and_counts(event_status) == [("counting", 2)]


@pytest.mark.parametrize(
    "counting",
    [
        pytest.param({}, id="uncounted"),
        pytest.param({"count": new_count(1, period=HOUR)}, id="counted"),
    ],
)
def test_event_of_a_delaying_rule_is_delayed(
    event_server: EventServer, event_status: EventStatus, counting: ec.Rule
) -> None:
    use_rules(event_server, new_rule(counting | {"delay": 60}))

    with time_machine.travel(START, tick=False):
        process_message(event_server, ec.Event(text="disk full"))

    assert [(event["phase"], event["delay_until"]) for event in event_status.events()] == [
        ("delayed", START + 60)
    ]


# fmt: off
@pytest.mark.parametrize(
    "counting, expected_history",
    [
        pytest.param({}, ["NEW", "AUTODELETE"], id="uncounted"),
        pytest.param({"count": new_count(1, period=HOUR)}, ["NEW", "COUNTREACHED", "AUTODELETE"], id="counted"),
    ],
)
# fmt: on
def test_event_of_an_autodeleting_rule_is_closed_immediately(
    event_server: EventServer,
    history: RecordingHistory,
    counting: ec.Rule,
    expected_history: list[str],
) -> None:
    use_rules(event_server, new_rule(counting | {"autodelete": True}))

    process_message(event_server, ec.Event(text="disk full"))

    assert history.whats == expected_history


def test_unmatched_message_is_archived_if_configured(
    event_server: EventServer, config: Config, history: RecordingHistory
) -> None:
    event_server.reload_configuration(config | {"archive_orphans": True}, history)

    process_message(event_server, ec.Event(text="disk full"))

    assert [(what, event["text"]) for what, event in history.entries] == [("ARCHIVED", "disk full")]


def test_messages_are_logged_if_configured(
    event_server: EventServer, settings: ec.Settings, config: Config, history: RecordingHistory
) -> None:
    event_server.reload_configuration(config | {"log_messages": True}, history)

    process_message(
        event_server,
        ec.Event(host=HostName("fileserver"), application="smartd", pid=42, text="disk full"),
    )

    [log_file] = settings.paths.messages_dir.value.glob("*.log")
    assert log_file.read_text().endswith(" fileserver smartd[42]: disk full\n")


@pytest.mark.parametrize(
    "mode, expected_number_of_events",
    [
        pytest.param("sync", 0, id="syncing"),
        pytest.param("takeover", 1, id="taken over"),
    ],
)
def test_replication_slave_processes_messages_only_after_taking_over(
    event_server: EventServer,
    event_status: EventStatus,
    config: Config,
    history: RecordingHistory,
    slave_status: SlaveStatus,
    mode: Literal["sync", "takeover"],
    expected_number_of_events: int,
) -> None:
    rule_packs = [ec.default_rule_pack([new_rule({})])]
    event_server.reload_configuration(
        replication_slave_config(config) | {"rule_packs": rule_packs}, history
    )
    slave_status["mode"] = mode

    event_server.process_syslog_messages([b"<11>Oct 22 13:05:00 fileserver smartd: disk full"], None)

    assert len(event_status.events()) == expected_number_of_events


@pytest.mark.parametrize(
    "cancelling_message, expected_rule_ids",
    [
        pytest.param({}, [], id="same host and application"),
        pytest.param({"host": "nas"}, ["disk"], id="other host"),
        pytest.param({"application": "smartd"}, ["disk"], id="other application"),
    ],
)
def test_only_events_of_the_same_origin_are_cancelled(
    event_server: EventServer,
    event_status: EventStatus,
    cancelling_message: ec.Event,
    expected_rule_ids: list[str],
) -> None:
    use_rules(event_server, new_rule({"id": "disk", "match": "disk failed", "match_ok": "disk ok"}))
    process_message(event_server, ec.Event(text="disk failed"))

    process_message(event_server, ec.Event(text="disk ok") | cancelling_message)

    assert [event["rule_id"] for event in event_status.events()] == expected_rule_ids


@pytest.mark.parametrize(
    "cancelling_text, expected_rule_ids",
    [
        pytest.param("disk sda ok", [], id="same disk"),
        pytest.param("disk sdb ok", ["disk"], id="other disk"),
    ],
)
def test_only_events_with_the_same_match_groups_are_cancelled(
    event_server: EventServer,
    event_status: EventStatus,
    cancelling_text: str,
    expected_rule_ids: list[str],
) -> None:
    use_rules(
        event_server,
        new_rule({"id": "disk", "match": r"disk (\S+) failed", "match_ok": r"disk (\S+) ok"}),
    )
    process_message(event_server, ec.Event(text="disk sda failed"))

    process_message(event_server, ec.Event(text=cancelling_text))

    assert [event["rule_id"] for event in event_status.events()] == expected_rule_ids

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import fcntl
import logging
import math
import os
import resource
import threading
import time
from collections.abc import Sequence
from contextlib import suppress
from typing import Literal, override

import pytest

import cmk.ec.export as ec
from cmk.ccc.hostaddress import HostName
from cmk.ec.config import Config, MatchGroups
from cmk.ec.event import Event
from cmk.ec.history import History, HistoryWhat
from cmk.ec.main import (
    create_history,
    EventServer,
    EventStatus,
    StatusTableEvents,
    StatusTableHistory,
)

from .helpers import (
    new_event,
    new_rule,
    process_message,
    RecordingHistory,
    wait_until_bytes_in_pipe,
)


def _make_rule(state: ec.State) -> ec.Rule:
    return new_rule({"id": "patterns", "state": state})


@pytest.mark.parametrize(
    "state,priority,expected",
    [
        pytest.param(-1, ec.SyslogPriority(0), 2, id="set by syslog, prio 0"),
        pytest.param(-1, ec.SyslogPriority(1), 2, id="set by syslog, prio 1"),
        pytest.param(-1, ec.SyslogPriority(2), 2, id="set by syslog, prio 2"),
        pytest.param(-1, ec.SyslogPriority(3), 2, id="set by syslog, prio 3"),
        pytest.param(-1, ec.SyslogPriority(4), 1, id="set by syslog, prio 4"),
        pytest.param(-1, ec.SyslogPriority(5), 0, id="set by syslog, prio 5"),
        pytest.param(-1, ec.SyslogPriority(6), 0, id="set by syslog, prio 6"),
        pytest.param(-1, ec.SyslogPriority(7), 0, id="set by syslog, prio 7"),
        pytest.param(0, ec.SyslogPriority(0), 0, id="set to OK"),
        pytest.param(1, ec.SyslogPriority(0), 1, id="set to WARN"),
        pytest.param(2, ec.SyslogPriority(0), 2, id="set to CRIT"),
        pytest.param(3, ec.SyslogPriority(0), 3, id="set to UNKNOWN"),
        pytest.param(
            ("text_pattern", {"0": "^UND.*as ", "1": "Lamm", "2": "HURZ"}),
            ec.SyslogPriority(0),
            2,
            id="set via text (CRIT)",
        ),
        pytest.param(
            ("text_pattern", {"0": "^UND.*as ", "1": "Lamm", "2": "foo"}),
            ec.SyslogPriority(0),
            1,
            id="set via text (WARN)",
        ),
        pytest.param(
            ("text_pattern", {"0": "^UND.*as ", "1": "foo", "2": "bar"}),
            ec.SyslogPriority(0),
            0,
            id="set via text (OK)",
        ),
        pytest.param(
            ("text_pattern", {"0": "^UND.*as ", "1": "Lamm"}),
            ec.SyslogPriority(0),
            1,
            id="set via text (OK, missing CRIT)",
        ),
        pytest.param(
            ("text_pattern", {"0": "^UND.*as ", "2": "foo"}),
            ec.SyslogPriority(0),
            0,
            id="set via text (OK, missing WARN)",
        ),
    ],
)
def test_rewrite_event_state(
    event_server: EventServer, state: ec.State, priority: ec.SyslogPriority, expected: int
) -> None:
    rule = _make_rule(state)
    ec.compile_rule(rule)
    event = new_event(
        ec.Event(
            host=HostName("heute"),
            text='Und das Lamm schrie: "Hurz!"',
            core_host=HostName("heute"),
            priority=priority.value,
        )
    )
    assert "state" not in event

    event_server.rewrite_event(rule=rule, event=event, match_groups=MatchGroups())

    assert event["state"] == expected


def test_compiling_the_rules_keeps_the_rule_packs_for_replication_intact(
    event_server: EventServer,
) -> None:
    rule_packs = [ec.default_rule_pack([_make_rule(("text_pattern", {"2": "ERR.*"}))])]

    event_server.compile_rules(rule_packs)

    assert rule_packs == [ec.default_rule_pack([_make_rule(("text_pattern", {"2": "ERR.*"}))])]


def _reload_configuration(
    event_server: EventServer,
    settings: ec.Settings,
    config: Config,
    rule_packs: Sequence[ec.ECRulePack],
) -> None:
    # Unlike SQLite, recording the history in files leaves nothing open after the test.
    config_rule_packs = config | {"rule_packs": rule_packs, "archive_mode": "file"}
    history = create_history(
        settings,
        config_rule_packs,
        logging.getLogger("cmk.mkeventd"),
        StatusTableEvents.columns,
        StatusTableHistory.columns,
    )
    event_server.reload_configuration(config_rule_packs, history=history)


def test_rule_which_cannot_be_compiled_does_not_match(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    # The rule would match any message, only one of its state patterns is an invalid regex.
    rule = _make_rule(("text_pattern", {"2": "(("}))
    _reload_configuration(event_server, settings, config, [ec.default_rule_pack([rule])])

    process_message(event_server, ec.Event(text="Something happened"))

    assert event_status.events() == []


def _rule(
    rule_id: str, *, disabled: bool = False, drop: bool | Literal["skip_pack"] = False
) -> ec.Rule:
    """Returns a rule which matches any message"""
    rule = _make_rule(0)
    rule["id"] = rule_id
    rule["disabled"] = disabled
    rule["drop"] = drop
    return rule


def _rule_pack(pack_id: str, *rules: ec.Rule, disabled: bool = False) -> ec.ECRulePackSpec:
    return ec.ECRulePackSpec(id=pack_id, title=pack_id, disabled=disabled, rules=list(rules))


def _rule_ids_of_events(event_status: EventStatus) -> list[str | None]:
    return [event["rule_id"] for event in event_status.events()]


def test_disabled_rule_packs_and_rules_are_ignored(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    rule_packs = [
        _rule_pack("disabled", _rule("in_disabled_pack"), disabled=True),
        _rule_pack("enabled", _rule("disabled", disabled=True), _rule("enabled")),
    ]
    _reload_configuration(event_server, settings, config, rule_packs)

    process_message(event_server, ec.Event(text="Something happened"))

    assert _rule_ids_of_events(event_status) == ["enabled"]


def test_a_rule_which_skips_its_rule_pack_skips_its_other_rules(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    rule_packs = [
        _rule_pack("skipped", _rule("skipping", drop="skip_pack"), _rule("skipped")),
        _rule_pack("next", _rule("next")),
    ]
    _reload_configuration(event_server, settings, config, rule_packs)

    process_message(event_server, ec.Event(text="Something happened"))

    assert _rule_ids_of_events(event_status) == ["next"]


def test_a_rule_which_drops_the_message_stops_processing_it(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    rule_packs = [_rule_pack("pack", _rule("dropping", drop=True), _rule("matching"))]
    _reload_configuration(event_server, settings, config, rule_packs)

    process_message(event_server, ec.Event(text="Something happened"))

    assert _rule_ids_of_events(event_status) == []


def test_a_cancelling_match_cancels_the_events_of_the_rule(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    rule = _rule("disk")
    rule["match"] = "disk failed"
    rule["match_ok"] = "disk ok"
    _reload_configuration(event_server, settings, config, [_rule_pack("pack", rule)])
    process_message(event_server, ec.Event(text="disk failed"))
    assert _rule_ids_of_events(event_status) == ["disk"]

    process_message(event_server, ec.Event(text="disk ok"))

    assert _rule_ids_of_events(event_status) == []


def test_a_host_name_which_cannot_be_translated_is_empty(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    # Nobody validates settings written by hand.
    config_with_translation = config | {"hostname_translation": {"regex": [("((", "x")]}}
    _reload_configuration(
        event_server, settings, config_with_translation, [_rule_pack("pack", _rule("matching"))]
    )

    process_message(event_server, ec.Event(text="Something happened"))

    assert [event["host"] for event in event_status.events()] == [""]


def test_message_cannot_break_the_housekeeping_by_setting_the_lifetime_of_its_event(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    _reload_configuration(event_server, settings, config, [_rule_pack("pack", _rule("matching"))])
    message = (
        b"<134>1 2026-10-23T10:00:00Z fileserver smartd - - "
        b'[Checkmk@18662 live_until="tomorrow"] disk full'
    )
    event_server.process_syslog_messages([message], None)

    event_server.do_housekeeping()

    assert [event["phase"] for event in event_status.events()] == ["open"]


_RULE_OPTIMIZER = [
    pytest.param(True, id="with rule optimizer"),
    pytest.param(False, id="without rule optimizer"),
]


@pytest.mark.parametrize("rule_optimizer", _RULE_OPTIMIZER)
@pytest.mark.parametrize(
    "priorities",
    [
        pytest.param((4, 0), id="descending range"),
        pytest.param((0, 4), id="ascending range"),
    ],
)
def test_rule_matches_messages_within_its_priority_range(
    event_server: EventServer,
    event_status: EventStatus,
    settings: ec.Settings,
    config: Config,
    rule_optimizer: bool,
    priorities: tuple[int, int],
) -> None:
    rule = _rule("critical")
    rule["match_priority"] = priorities
    _reload_configuration(
        event_server, settings, config | {"rule_optimizer": rule_optimizer}, [_rule_pack("p", rule)]
    )

    process_message(event_server, ec.Event(text="Something happened", priority=2))

    assert _rule_ids_of_events(event_status) == ["critical"]


@pytest.mark.parametrize("rule_optimizer", _RULE_OPTIMIZER)
@pytest.mark.parametrize(
    "cancel_priorities",
    [
        pytest.param((7, 5), id="descending range"),
        pytest.param((5, 7), id="ascending range"),
    ],
)
def test_message_within_the_cancel_priority_range_cancels_the_event(
    event_server: EventServer,
    event_status: EventStatus,
    settings: ec.Settings,
    config: Config,
    rule_optimizer: bool,
    cancel_priorities: tuple[int, int],
) -> None:
    rule = _rule("critical")
    rule["match_priority"] = (2, 0)
    rule["cancel_priority"] = cancel_priorities
    _reload_configuration(
        event_server, settings, config | {"rule_optimizer": rule_optimizer}, [_rule_pack("p", rule)]
    )
    process_message(event_server, ec.Event(text="Disk failed", priority=2))
    assert _rule_ids_of_events(event_status) == ["critical"]

    process_message(event_server, ec.Event(text="Disk OK", priority=6))

    assert _rule_ids_of_events(event_status) == []


@pytest.mark.parametrize("rule_optimizer", _RULE_OPTIMIZER)
@pytest.mark.parametrize(
    "priorities",
    [
        pytest.param((8, 0), id="descending range"),
        pytest.param((0, 8), id="ascending range"),
    ],
)
def test_rule_with_a_priority_beyond_debug_is_ignored(
    event_server: EventServer,
    event_status: EventStatus,
    settings: ec.Settings,
    config: Config,
    rule_optimizer: bool,
    priorities: tuple[int, int],
) -> None:
    # Nobody validates rules written by hand.
    invalid_rule = _rule("invalid")
    invalid_rule["match_priority"] = priorities
    _reload_configuration(
        event_server,
        settings,
        config | {"rule_optimizer": rule_optimizer},
        [_rule_pack("p", invalid_rule, _rule("valid"))],
    )

    process_message(event_server, ec.Event(text="Something happened", priority=2))

    assert _rule_ids_of_events(event_status) == ["valid"]


@pytest.mark.parametrize(
    "rule_optimizer",
    [
        pytest.param(True, id="switching it off"),
        pytest.param(False, id="switching it on"),
    ],
)
def test_rules_match_while_a_reload_switches_the_rule_optimizer(
    event_server: EventServer,
    event_status: EventStatus,
    config: Config,
    history: History,
    rule_optimizer: bool,
) -> None:
    reloaded_config = config | {
        "rule_optimizer": rule_optimizer,
        "rule_packs": [_rule_pack("p", _rule("matching"))],
    }
    event_server.reload_configuration(reloaded_config, history)
    # Like during a further reload, the setting changes before the rules compiled for it replace
    # the current ones.
    reloaded_config["rule_optimizer"] = not rule_optimizer

    process_message(event_server, ec.Event(text="Something happened"))

    assert _rule_ids_of_events(event_status) == ["matching"]


def test_rule_hits_of_a_changed_rule_start_over_once_the_event_server_uses_it(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    _reload_configuration(event_server, settings, config, [_rule_pack("pack", _rule("changed"))])
    process_message(event_server, ec.Event(text="Something happened"))
    edited_rule = _rule("changed")
    edited_rule["description"] = "edited"
    _reload_configuration(event_server, settings, config, [_rule_pack("pack", edited_rule)])

    process_message(event_server, ec.Event(text="Something happened"))

    assert list(event_status.get_rule_stats()) == [("changed", 1)]


def test_a_message_counts_no_hit_of_a_rule_a_reload_changed_since_it_matched(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    _reload_configuration(
        event_server, settings, config, [_rule_pack("pack", _rule("changed"), _rule("unchanged"))]
    )
    # The message ran through these rules ...
    rule_digests = event_status.rule_digests
    edited_rule = _rule("changed")
    edited_rule["description"] = "edited"
    # ... before the reload, but counts its hits after it.
    _reload_configuration(
        event_server, settings, config, [_rule_pack("pack", edited_rule, _rule("unchanged"))]
    )

    event_status.count_rule_match("changed", rule_digests=rule_digests)
    event_status.count_rule_match("unchanged", rule_digests=rule_digests)

    assert list(event_status.get_rule_stats()) == [("unchanged", 1)]


def test_created_event_pipe_takes_messages_before_serving(
    event_server: EventServer, settings: ec.Settings
) -> None:
    event_server.create_pipe()

    # Without a reader, opening a FIFO for writing without blocking fails with ENXIO.
    writer = os.open(settings.paths.event_pipe.value, os.O_WRONLY | os.O_NONBLOCK)
    try:
        bytes_written = os.write(writer, b"something happened\n")
    finally:
        os.close(writer)

    assert bytes_written == len(b"something happened\n")


def test_closed_event_pipe_is_removed(event_server: EventServer, settings: ec.Settings) -> None:
    event_server.create_pipe()

    event_server.close_pipe()

    assert not settings.paths.event_pipe.value.exists()


def test_event_pipe_someone_else_removed_can_be_closed(
    event_server: EventServer, settings: ec.Settings
) -> None:
    event_server.create_pipe()
    settings.paths.event_pipe.value.unlink()

    event_server.close_pipe()


def test_event_pipe_that_cannot_be_removed_is_an_error(
    event_server: EventServer, settings: ec.Settings
) -> None:
    event_server.create_pipe()
    path = settings.paths.event_pipe.value
    # unlink() can't remove a directory.
    path.unlink()
    path.mkdir()

    with pytest.raises(IsADirectoryError):
        event_server.close_pipe()


def test_event_pipe_is_closed_even_if_it_cannot_be_removed(
    event_server: EventServer, settings: ec.Settings
) -> None:
    event_server.create_pipe()
    path = settings.paths.event_pipe.value
    writer = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
    try:
        # unlink() can't remove a directory.
        path.unlink()
        path.mkdir()

        with suppress(IsADirectoryError):
            event_server.close_pipe()

        # Without a reader, writing to a pipe fails.
        with pytest.raises(BrokenPipeError):
            os.write(writer, b"something happened\n")
    finally:
        os.close(writer)


def test_messages_left_in_closed_event_pipe_are_processed(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    _reload_configuration(event_server, settings, config, [_rule_pack("pack", _rule("any"))])
    event_server.create_pipe()
    writer = os.open(settings.paths.event_pipe.value, os.O_WRONLY | os.O_NONBLOCK)
    try:
        os.write(writer, b"first\nsecond\nincomplete")
    finally:
        os.close(writer)

    event_server.close_pipe()

    assert _texts_of_events(event_status) == ["first", "second"]


def test_message_of_writer_blocked_on_full_event_pipe_is_processed_on_closing(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    _reload_configuration(event_server, settings, config, [_rule_pack("pack", _rule("any"))])
    event_server.create_pipe()
    writer = os.open(settings.paths.event_pipe.value, os.O_WRONLY)
    # A pipe of a single page, so that a page of filler and a message block the daemonic writer
    page_size = fcntl.fcntl(writer, fcntl.F_SETPIPE_SZ, resource.getpagesize())
    filler = "x" * (page_size - 1)
    errors: list[OSError] = []
    thread = threading.Thread(
        target=_write_all_and_close,
        args=(writer, f"{filler}\nsomething happened\n".encode(), errors),
        daemon=True,
    )
    thread.start()
    wait_until_bytes_in_pipe(writer, page_size)

    _close_pipe_once_writers_closed_it(event_server)

    thread.join(timeout=30)
    assert (errors, _texts_of_events(event_status)) == ([], [filler, "something happened"])


def test_messages_left_in_event_pipe_that_cannot_be_removed_are_processed(
    event_server: EventServer, event_status: EventStatus, settings: ec.Settings, config: Config
) -> None:
    _reload_configuration(event_server, settings, config, [_rule_pack("pack", _rule("any"))])
    event_server.create_pipe()
    path = settings.paths.event_pipe.value
    writer = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
    try:
        os.write(writer, b"something happened\n")
    finally:
        os.close(writer)
    # unlink() can't remove a directory.
    path.unlink()
    path.mkdir()

    with suppress(IsADirectoryError):
        event_server.close_pipe()

    assert _texts_of_events(event_status) == ["something happened"]


def _close_pipe_once_writers_closed_it(event_server: EventServer) -> None:
    """
    Closes the event pipe once its writers have closed it, however long they take: The clock stands
    still, and the timeout is below the idle timeout, so that nothing counts as idle.
    """
    clock = _ClockStandingStill()
    event_server.close_pipe(timeout=1.0, idle_timeout=2.0, clock=clock)
    assert not clock.jumped, "closing didn't end once the writers had closed the event pipe"


class _ClockStandingStill:
    """
    A clock standing still, but jumping past any timeout after 30 s of real time, so that a failing
    test doesn't hang
    """

    def __init__(self) -> None:
        self._real_deadline = time.monotonic() + 30
        self.jumped = False

    def __call__(self) -> float:
        if time.monotonic() < self._real_deadline:
            return 0.0
        self.jumped = True
        return math.inf


class _HistoryFailingFor(RecordingHistory):
    """Fails to record anything about the events with the given text"""

    def __init__(self, text: str) -> None:
        super().__init__()
        self._text = text

    @override
    def add(self, event: Event, what: HistoryWhat, who: str = "", addinfo: str = "") -> None:
        if event["text"] == self._text:
            raise OSError("disk full")
        super().add(event, what, who, addinfo)


def test_message_failing_on_closing_the_event_pipe_doesnt_drop_the_messages_after_it(
    event_server: EventServer, event_status: EventStatus, config: Config, settings: ec.Settings
) -> None:
    event_server.create_pipe()
    writer = os.open(settings.paths.event_pipe.value, os.O_WRONLY)
    # A pipe of a single page, so that the failing filler and the message arrive separately
    page_size = fcntl.fcntl(writer, fcntl.F_SETPIPE_SZ, resource.getpagesize())
    filler = "x" * (page_size - 1)
    history = _HistoryFailingFor(filler)
    rule_config = config | {"rule_packs": [_rule_pack("pack", _rule("any"))]}
    event_server.reload_configuration(rule_config, history)
    event_status.reload_configuration(rule_config, history)
    thread = threading.Thread(
        target=_write_all_and_close,
        args=(writer, f"{filler}\nsomething happened\n".encode(), []),
        daemon=True,
    )
    thread.start()
    wait_until_bytes_in_pipe(writer, page_size)

    _close_pipe_once_writers_closed_it(event_server)

    thread.join(timeout=30)
    assert _texts_of_events(event_status) == [filler, "something happened"]


class _HistoryWritingFor(RecordingHistory):
    """Writes the data once when recording an event with the given text, like a busy writer"""

    def __init__(self, text: str, fd: int, data: bytes) -> None:
        super().__init__()
        self._text = text
        self._fd = fd
        self._data: bytes | None = data

    @override
    def add(self, event: Event, what: HistoryWhat, who: str = "", addinfo: str = "") -> None:
        if event["text"] == self._text and self._data is not None:
            os.write(self._fd, self._data)
            self._data = None
        super().add(event, what, who, addinfo)


def test_message_still_arriving_in_closed_event_pipe_at_the_timeout_is_dropped(
    event_server: EventServer, event_status: EventStatus, config: Config, settings: ec.Settings
) -> None:
    event_server.create_pipe()
    writer = os.open(settings.paths.event_pipe.value, os.O_WRONLY | os.O_NONBLOCK)
    try:
        # The writer writes the 2nd message while the event server processes the 1st one.
        history = _HistoryWritingFor("first", writer, b"second\n")
        rule_config = config | {"rule_packs": [_rule_pack("pack", _rule("any"))]}
        event_server.reload_configuration(rule_config, history)
        event_status.reload_configuration(rule_config, history)
        os.write(writer, b"first\n")

        # The timeout runs out once the 1st message is processed, however long that takes.
        event_server.close_pipe(clock=lambda: math.inf if _texts_of_events(event_status) else 0.0)
    finally:
        os.close(writer)

    assert _texts_of_events(event_status) == ["first"]


def test_messages_left_in_closed_event_pipe_after_the_timeout_are_dropped_with_a_warning(
    event_server: EventServer,
    event_status: EventStatus,
    settings: ec.Settings,
    config: Config,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)
    _reload_configuration(event_server, settings, config, [_rule_pack("pack", _rule("any"))])
    event_server.create_pipe()
    writer = os.open(settings.paths.event_pipe.value, os.O_WRONLY | os.O_NONBLOCK)
    try:
        os.write(writer, b"first\n")

        event_server.close_pipe(timeout=0)
    finally:
        os.close(writer)

    assert (caplog.messages, _texts_of_events(event_status)) == (
        ["Processing the event pipe on stopping took too long, dropping the 6 bytes left"],
        [],
    )


@pytest.mark.parametrize(
    "start",
    [
        pytest.param(b"incomplete", id="short"),
        pytest.param(b"x" * 100, id="long"),
    ],
)
def test_start_of_a_message_already_read_counts_as_dropped_at_the_timeout(
    event_server: EventServer,
    event_status: EventStatus,
    settings: ec.Settings,
    config: Config,
    caplog: pytest.LogCaptureFixture,
    start: bytes,
) -> None:
    caplog.set_level(logging.WARNING)
    _reload_configuration(event_server, settings, config, [_rule_pack("pack", _rule("any"))])
    event_server.create_pipe()
    writer = os.open(settings.paths.event_pipe.value, os.O_WRONLY | os.O_NONBLOCK)
    try:
        os.write(writer, b"first\n" + start)

        # The timeout runs out once the 1st message is processed, however long that takes.
        event_server.close_pipe(clock=lambda: math.inf if _texts_of_events(event_status) else 0.0)
    finally:
        os.close(writer)

    assert caplog.messages == [
        f"Processing the event pipe on stopping took too long, dropping the {len(start)} bytes left"
    ]


def test_start_of_a_message_whose_rest_doesnt_arrive_is_dropped_with_a_warning(
    event_server: EventServer, settings: ec.Settings, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    event_server.create_pipe()
    writer = os.open(settings.paths.event_pipe.value, os.O_WRONLY | os.O_NONBLOCK)
    try:
        os.write(writer, b"incomplete")

        # With a clock standing still, only the idle writer can end the wait.
        event_server.close_pipe(timeout=1.0, idle_timeout=0.1, clock=_ClockStandingStill())
    finally:
        os.close(writer)

    assert caplog.messages == [
        "The rest of a message didn't arrive in the event pipe on stopping, dropping the 10 bytes left"
    ]


def test_waiting_for_the_rest_of_a_message_until_the_timeout_is_no_idle_writer(
    event_server: EventServer, settings: ec.Settings, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    event_server.create_pipe()
    writer = os.open(settings.paths.event_pipe.value, os.O_WRONLY | os.O_NONBLOCK)
    try:
        os.write(writer, b"incomplete")

        # Without an idle timeout, only the timeout can cut the wait for the rest short.
        event_server.close_pipe(timeout=0.1, idle_timeout=math.inf)
    finally:
        os.close(writer)

    assert caplog.messages == [
        "Processing the event pipe on stopping took too long, dropping the 10 bytes left"
    ]


def test_start_of_a_message_whose_writer_closed_the_event_pipe_is_dropped_with_a_warning(
    event_server: EventServer, settings: ec.Settings, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    event_server.create_pipe()
    writer = os.open(settings.paths.event_pipe.value, os.O_WRONLY | os.O_NONBLOCK)
    try:
        os.write(writer, b"incomplete")
    finally:
        os.close(writer)

    _close_pipe_once_writers_closed_it(event_server)

    assert caplog.messages == [
        "The rest of a message didn't arrive in the event pipe on stopping, dropping the 10 bytes left"
    ]


def test_idle_writer_keeping_closed_event_pipe_open_doesnt_hold_up_closing(
    event_server: EventServer, settings: ec.Settings
) -> None:
    event_server.create_pipe()
    writer = os.open(settings.paths.event_pipe.value, os.O_WRONLY | os.O_NONBLOCK)
    # With a clock standing still, only the idle writer can end the wait.
    clock = _ClockStandingStill()
    try:
        event_server.close_pipe(timeout=1.0, idle_timeout=0.1, clock=clock)

        # Without a reader, writing to a pipe fails.
        with pytest.raises(BrokenPipeError):
            os.write(writer, b"something happened\n")
    finally:
        os.close(writer)

    assert not clock.jumped


def test_writer_keeping_closed_event_pipe_open_is_no_warning(
    event_server: EventServer, settings: ec.Settings, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    event_server.create_pipe()
    writer = os.open(settings.paths.event_pipe.value, os.O_WRONLY | os.O_NONBLOCK)
    try:
        event_server.close_pipe(timeout=0)
    finally:
        os.close(writer)

    assert caplog.messages == []


class _PipeExistenceWhileLogging(logging.Handler):
    """Records whether the event pipe exists when logging a message with the given beginning"""

    def __init__(self, beginning: str, settings: ec.Settings) -> None:
        super().__init__()
        self._beginning = beginning
        self._pipe = settings.paths.event_pipe.value
        self.existence: list[bool] = []

    @override
    def emit(self, record: logging.LogRecord) -> None:
        if record.getMessage().startswith(self._beginning):
            self.existence.append(self._pipe.exists())


def test_event_server_reports_its_termination_once_it_has_removed_the_event_pipe(
    event_server: EventServer, settings: ec.Settings, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="cmk.mkeventd.EventServer")
    event_server.create_pipe()
    pipe_existence = _PipeExistenceWhileLogging("Terminated", settings)
    logger = logging.getLogger("cmk.mkeventd.EventServer")
    logger.addHandler(pipe_existence)
    # A daemon thread doesn't keep pytest from exiting if it doesn't terminate.
    event_server.daemon = True
    try:
        # Before starting it, so that it doesn't serve without the sockets main() opens
        event_server.terminate()

        event_server.start()
        event_server.join(timeout=30)
    finally:
        logger.removeHandler(pipe_existence)

    assert pipe_existence.existence == [False]


def _texts_of_events(event_status: EventStatus) -> list[str]:
    return [event["text"] for event in event_status.events()]


def _write_all_and_close(fd: int, data: bytes, errors: list[OSError]) -> None:
    try:
        while data:
            data = data[os.write(fd, data) :]
    except OSError as e:
        errors.append(e)
    finally:
        os.close(fd)

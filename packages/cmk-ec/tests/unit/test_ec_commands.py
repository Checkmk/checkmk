#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Commands sent to the status socket of the EC"""

import ast
import fcntl
import itertools
import math
import os
import resource
import threading
import time
from collections.abc import Callable
from typing import Literal

import pytest

import cmk.ec.export as ec
from cmk.ec.config import Config
from cmk.ec.history import History
from cmk.ec.main import EventServer, EventStatus, SlaveStatus, StatusServer
from cmk.ec.query import MKClientError

from .helpers import (
    FakeStatusSocket,
    MakeStatusServer,
    new_event,
    query_status_server,
    replication_slave_config,
    wait_until_bytes_in_pipe,
)


def _command(status_server: StatusServer, command: str, *, allow_commands: bool = True) -> None:
    query_status_server(status_server, f"COMMAND {command}", allow_commands=allow_commands)


def _become_replication_slave(
    status_server: StatusServer, config: Config, history: History
) -> None:
    status_server.reload_configuration(replication_slave_config(config), history)


@pytest.mark.parametrize(
    "arguments, expected_rule_hits",
    [
        pytest.param(";disk", [("cpu", 1)], id="of one rule"),
        pytest.param("", [], id="of all rules"),
    ],
)
def test_resetting_counters_forgets_rule_hits(
    event_status: EventStatus,
    status_server: StatusServer,
    arguments: str,
    expected_rule_hits: list[tuple[str, int]],
) -> None:
    event_status.count_rule_match("cpu", rule_digests=event_status.rule_digests)
    event_status.count_rule_match("disk", rule_digests=event_status.rule_digests)

    _command(status_server, f"RESETCOUNTERS{arguments}")

    assert list(event_status.get_rule_stats()) == expected_rule_hits


def test_flushing_deletes_all_events(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.new_event(new_event(ec.Event(text="disk full")))

    _command(status_server, "FLUSH")

    assert event_status.events() == []


def test_syncing_saves_the_events(
    settings: ec.Settings, event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.new_event(new_event(ec.Event(text="disk full")))

    _command(status_server, "SYNC")

    saved_status = ast.literal_eval(settings.paths.status_file.value.read_text())
    assert [event["text"] for event in saved_status["events"]] == ["disk full"]


@pytest.mark.parametrize("mode", ["sync", "takeover"])
def test_replication_slave_switches_to_the_requested_mode(
    config: Config,
    history: History,
    slave_status: SlaveStatus,
    status_server: StatusServer,
    mode: Literal["sync", "takeover"],
) -> None:
    _become_replication_slave(status_server, config, history)

    _command(status_server, f"SWITCHMODE;{mode}")

    assert slave_status["mode"] == mode


def test_replication_slave_refuses_to_switch_to_an_unknown_mode(
    config: Config, history: History, status_server: StatusServer
) -> None:
    _become_replication_slave(status_server, config, history)

    with pytest.raises(MKClientError, match="Invalid target mode master"):
        _command(status_server, "SWITCHMODE;master")


def test_master_refuses_to_switch_its_replication_mode(status_server: StatusServer) -> None:
    with pytest.raises(MKClientError, match="this is not a replication slave"):
        _command(status_server, "SWITCHMODE;sync")


def test_reloading_is_requested(
    status_server: StatusServer, reload_config_event: threading.Event
) -> None:
    _command(status_server, "RELOAD")

    assert reload_config_event.is_set()


def test_shutting_down_is_requested(
    status_server: StatusServer, terminate_main_event: threading.Event
) -> None:
    _command(status_server, "SHUTDOWN")

    assert terminate_main_event.is_set()


def test_created_message_is_passed_unchanged_to_the_event_pipe(
    settings: ec.Settings, event_server: EventServer, status_server: StatusServer
) -> None:
    event_server.create_pipe()

    _command(status_server, "CREATE;disk /var full; 98% used")

    assert _read_event_pipe(settings) == b"disk /var full; 98% used\n"


def test_created_message_puts_no_file_in_place_of_a_removed_event_pipe(
    settings: ec.Settings, status_server: StatusServer
) -> None:
    # Like after the event server removed the event pipe on terminating
    with pytest.raises(MKClientError, match="No such file or directory"):
        _command(status_server, "CREATE;disk /var full; 98% used")

    assert not settings.paths.event_pipe.value.exists()


def test_created_message_doesnt_overwrite_a_regular_file_in_place_of_the_event_pipe(
    settings: ec.Settings, status_server: StatusServer
) -> None:
    path = settings.paths.event_pipe.value
    path.write_bytes(b"something important\n")

    with pytest.raises(MKClientError, match="Not a FIFO"):
        _command(status_server, "CREATE;disk /var full; 98% used")

    assert path.read_bytes() == b"something important\n"


def test_created_message_for_an_event_pipe_nobody_reads_is_an_error(
    settings: ec.Settings, status_server: StatusServer
) -> None:
    # Like after the event server couldn't remove the event pipe on terminating
    os.mkfifo(settings.paths.event_pipe.value)

    with pytest.raises(MKClientError, match="No such device or address"):
        _command(status_server, "CREATE;disk /var full; 98% used")


def test_created_message_that_cannot_be_written_gets_no_answer(
    status_server: StatusServer,
) -> None:
    # Like after the event server removed the event pipe on terminating
    status_socket = FakeStatusSocket(b"COMMAND CREATE;disk /var full; 98% used")

    with pytest.raises(MKClientError, match="No such file or directory"):
        status_server.handle_client(status_socket, True, "127.0.0.1")

    assert status_socket.get_raw_response() == b""


def test_created_message_waits_for_room_in_the_event_pipe_without_holding_the_lock(
    settings: ec.Settings,
    event_server: EventServer,
    event_status: EventStatus,
    status_server: StatusServer,
) -> None:
    event_server.create_pipe()
    path = settings.paths.event_pipe.value
    reader = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        # A pipe of two pages, one of them full, and a message longer than a page, so that a part
        # goes in
        page_size = fcntl.fcntl(reader, fcntl.F_SETPIPE_SZ, 2 * resource.getpagesize()) // 2
        filler = b"x" * page_size
        writer = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
        try:
            os.write(writer, filler)
        finally:
            os.close(writer)
        message = "y" * (page_size + 1000)
        # A daemon thread doesn't keep pytest from exiting if it stays blocked.
        thread = threading.Thread(
            target=_command, args=(status_server, f"CREATE;{message}"), daemon=True
        )
        thread.start()
        wait_until_bytes_in_pipe(reader, 2 * page_size)

        # The event server needs the lock to process what it reads from the pipe.
        assert event_status.lock.acquire(timeout=30), "CREATE holds the lock while waiting"
        event_status.lock.release()
        received = os.read(reader, 65536)
        thread.join(timeout=30)
        received += os.read(reader, 65536)
    finally:
        os.close(reader)

    assert received == filler + f"{message}\n".encode()


def test_created_message_for_an_event_pipe_staying_full_is_an_error(
    settings: ec.Settings, event_server: EventServer, make_status_server: MakeStatusServer
) -> None:
    event_server.create_pipe()
    filler = _fill_event_pipe(settings)
    status_server = make_status_server(_clock_running_out_after_the_start())

    with pytest.raises(MKClientError, match="Still full after 5 seconds"):
        _command(status_server, "CREATE;disk /var full; 98% used")

    assert _read_event_pipe(settings) == filler


def test_created_message_waits_for_room_in_a_full_event_pipe(
    settings: ec.Settings, event_server: EventServer, make_status_server: MakeStatusServer
) -> None:
    event_server.create_pipe()
    filler = _fill_event_pipe(settings)
    clock = _ClockStandingStill()
    errors: list[Exception] = []
    # A daemon thread doesn't keep pytest from exiting if it stays blocked.
    thread = threading.Thread(
        target=_command_recording_errors,
        args=(make_status_server(clock), "CREATE;disk /var full; 98% used", errors),
        daemon=True,
    )

    thread.start()
    waited = clock.asked_again.wait(timeout=30)  # i.e. making room only once CREATE waits for it
    received = _read_event_pipe(settings)
    thread.join(timeout=30)
    received += _read_event_pipe(settings)

    assert (waited, errors, clock.jumped, received) == (
        True,
        [],
        False,
        filler + b"disk /var full; 98% used\n",
    )


def test_created_message_begun_is_finished_after_the_deadline(
    settings: ec.Settings, event_server: EventServer, make_status_server: MakeStatusServer
) -> None:
    event_server.create_pipe()
    path = settings.paths.event_pipe.value
    reader = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        # A pipe of two pages, one of them full, and a message longer than a page, so that a part
        # goes in
        page_size = fcntl.fcntl(reader, fcntl.F_SETPIPE_SZ, 2 * resource.getpagesize()) // 2
        filler = b"x" * page_size
        writer = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
        try:
            os.write(writer, filler)
        finally:
            os.close(writer)
        message = "y" * (page_size + 1000)
        errors: list[Exception] = []
        # A daemon thread doesn't keep pytest from exiting if it stays blocked.
        thread = threading.Thread(
            target=_command_recording_errors,
            args=(
                make_status_server(_clock_running_out_after_the_start()),
                f"CREATE;{message}",
                errors,
            ),
            daemon=True,
        )

        thread.start()
        wait_until_bytes_in_pipe(reader, 2 * page_size)
        received = os.read(reader, 65536)
        thread.join(timeout=30)
        received += os.read(reader, 65536)
    finally:
        os.close(reader)

    assert (errors, received) == ([], filler + f"{message}\n".encode())


def _fill_event_pipe(settings: ec.Settings) -> bytes:
    """Fills the event pipe, which then holds a single page, returning what's in it"""
    writer = os.open(settings.paths.event_pipe.value, os.O_WRONLY | os.O_NONBLOCK)
    try:
        filler = b"x" * fcntl.fcntl(writer, fcntl.F_SETPIPE_SZ, resource.getpagesize())
        os.write(writer, filler)
    finally:
        os.close(writer)
    return filler


def _clock_running_out_after_the_start() -> Callable[[], float]:
    """A clock running out any timeout once asked again, i.e. once CREATE waits for room"""
    times = itertools.chain([0.0], itertools.repeat(math.inf))
    return lambda: next(times)


class _ClockStandingStill:
    """
    A clock standing still, which tells when it gets asked again, i.e. once CREATE waits for room,
    but jumps past any timeout after 30 s of real time, so that a failing test doesn't hang
    """

    def __init__(self) -> None:
        self._real_deadline = time.monotonic() + 30
        self._asked = 0
        self.asked_again = threading.Event()
        self.jumped = False

    def __call__(self) -> float:
        self._asked += 1
        if self._asked > 1:
            self.asked_again.set()
        if time.monotonic() < self._real_deadline:
            return 0.0
        self.jumped = True
        return math.inf


def _command_recording_errors(
    status_server: StatusServer, command: str, errors: list[Exception]
) -> None:
    try:
        _command(status_server, command)
    except Exception as e:
        errors.append(e)


def _read_event_pipe(settings: ec.Settings) -> bytes:
    # Without blocking, as the event server's own writer keeps reading from hitting EOF
    reader = os.open(settings.paths.event_pipe.value, os.O_RDONLY | os.O_NONBLOCK)
    try:
        return os.read(reader, 65536)
    finally:
        os.close(reader)


def test_user_executing_an_action_becomes_the_owner_of_the_event(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.new_event(new_event(ec.Event(text="disk full")))

    _command(status_server, "ACTION;1;harry;@NOTIFY")

    assert [event["owner"] for event in event_status.events()] == ["harry"]


def test_undefined_action_is_refused(
    event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.new_event(new_event(ec.Event(text="disk full")))

    with pytest.raises(MKClientError, match="The action 'reboot' is not defined"):
        _command(status_server, "ACTION;1;harry;reboot")


def test_updating_a_nonexistent_event_is_refused(status_server: StatusServer) -> None:
    with pytest.raises(MKClientError, match="No event with id 1"):
        _command(status_server, "UPDATE;1;harry;1;my comment;my contact")


@pytest.mark.parametrize(
    "command",
    [
        pytest.param("DELETE;1", id="DELETE"),
        pytest.param("DELETE_EVENTS_OF_HOST;fileserver", id="DELETE_EVENTS_OF_HOST"),
    ],
)
def test_deleting_without_a_user_is_refused(status_server: StatusServer, command: str) -> None:
    with pytest.raises(MKClientError, match="Wrong number of arguments"):
        _command(status_server, command)


@pytest.mark.parametrize(
    "command",
    [
        pytest.param("DELETE;1;harry", id="DELETE"),
        pytest.param("UPDATE;1;harry;1;my comment;my contact", id="UPDATE"),
        pytest.param("CHANGESTATE;1;harry;2", id="CHANGESTATE"),
        pytest.param("ACTION;1;harry;@NOTIFY", id="ACTION"),
        pytest.param("DELETE_EVENTS_OF_HOST;fileserver;harry", id="DELETE_EVENTS_OF_HOST"),
    ],
)
def test_syncing_replication_slave_refuses_to_change_events(
    config: Config,
    history: History,
    slave_status: SlaveStatus,
    status_server: StatusServer,
    command: str,
) -> None:
    _become_replication_slave(status_server, config, history)
    slave_status["mode"] = "sync"

    with pytest.raises(MKClientError, match="not allowed on a replication slave"):
        _command(status_server, command)


def test_syncing_replication_slave_resets_its_rule_hits(
    config: Config,
    history: History,
    event_status: EventStatus,
    slave_status: SlaveStatus,
    status_server: StatusServer,
) -> None:
    # The GUI resets the rule hits on all sites, and the next sync replaces them anyway.
    _become_replication_slave(status_server, config, history)
    slave_status["mode"] = "sync"
    event_status.count_rule_match("disk", rule_digests=event_status.rule_digests)

    _command(status_server, "RESETCOUNTERS")

    assert list(event_status.get_rule_stats()) == []


def test_commands_are_refused_where_disallowed(status_server: StatusServer) -> None:
    with pytest.raises(MKClientError, match="Commands are disallowed via TCP"):
        _command(status_server, "RELOAD", allow_commands=False)


def test_unknown_command_is_refused(status_server: StatusServer) -> None:
    with pytest.raises(MKClientError, match="Unknown command REBOOT"):
        _command(status_server, "REBOOT")

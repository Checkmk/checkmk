#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import logging
import os
import socket
import tempfile
import time
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import NamedTuple

import pytest

import cmk.ec.export as ec
from cmk.ccc.site import SiteId
from cmk.ec.config import Config
from cmk.ec.helpers import ECLock
from cmk.ec.history import History
from cmk.ec.main import (
    create_history,
    create_history_raw,
    default_slave_status_master,
    EventServer,
    EventStatus,
    make_config,
    StatusTableEvents,
    StatusTableHistory,
)
from cmk.ec.perfcounters import Perfcounters
from cmk.ec.query import Columns
from cmk.ec.settings import create_settings

_RECEIVE_TIMEOUT = 10  # seconds
_TERMINATE_TIMEOUT = 10  # seconds
# How long to wait for events beyond the expected ones, so a test sees surplus events, too
_SURPLUS_EVENTS_TIMEOUT = 0.1  # seconds
# Instead of a second, so tests don't wait that long for restarts
_EVENT_SERVER_DELAY = 0.01  # seconds

_MATCHING_ALL = ec.Rule(
    id="all",
    actions=[],
    actions_in_downtime=True,
    autodelete=False,
    cancel_action_phases="always",
    cancel_actions=[],
    comment="",
    description="",
    disabled=False,
    docu_url="",
    invert_matching=False,
    sl=ec.ServiceLevel(precedence="message", value=0),
    state=0,
)


class _CoreWithoutHosts:
    """Answers the host lookups of the Event Console like a monitoring core without any hosts"""

    def __init__(self) -> None:
        self.unexpected_queries: list[str] = []

    def query(self, query: str) -> Sequence[Sequence[object]]:
        match query.splitlines():
            case ["GET status", "Columns: program_start"]:
                return [[0]]
            case ["GET hosts", *_]:
                return []
            case _:
                self.unexpected_queries.append(query)
                raise ValueError(f"unexpected Livestatus query {query!r}")


class _EventConsole(NamedTuple):
    settings: ec.Settings
    event_status: EventStatus


type _HistoryFactory = Callable[[ec.Settings, Config, logging.Logger, Columns, Columns], History]


@pytest.fixture(name="event_console")
def fixture_event_console() -> Iterator[_EventConsole]:
    with _running_event_console(create_history) as event_console:
        yield event_console


@contextlib.contextmanager
def _running_event_console(make_history: _HistoryFactory) -> Iterator[_EventConsole]:
    """A running event server, wired up like by main(), opening an event for each message"""
    # Unix socket paths are limited to ~108 bytes, which pytest's tmp_path may exceed.
    with tempfile.TemporaryDirectory(dir="/tmp") as omd_root:
        settings = create_settings("1.2.3i45", Path(omd_root), ["mkeventd"])
        settings.paths.event_pipe.value.parent.mkdir(parents=True)
        logger = logging.getLogger("cmk.mkeventd")
        # Unlike SQLite, recording the history in files leaves nothing open after the test.
        config = make_config(ec.default_config()) | {"archive_mode": "file"}
        history = make_history(
            settings, config, logger, StatusTableEvents.columns, StatusTableHistory.columns
        )
        perfcounters = Perfcounters(logger.getChild("lock.perfcounters"))
        core = _CoreWithoutHosts()
        event_status = EventStatus(
            settings, config, perfcounters, history, logger.getChild("EventStatus"), core
        )
        event_server = EventServer(
            logger.getChild("EventServer"),
            settings,
            config,
            default_slave_status_master(),
            perfcounters,
            ECLock(logger.getChild("lock.configuration")),
            history,
            event_status,
            StatusTableEvents.columns,
            core,
            SiteId("hurz"),
            restart_delay=_EVENT_SERVER_DELAY,
        )
        event_server.compile_rules([ec.default_rule_pack([_MATCHING_ALL])])
        # So that an event server which doesn't terminate fails the test instead of hanging it
        event_server.daemon = True
        event_server.start()
        try:
            yield _EventConsole(settings, event_status)
        finally:
            event_server.terminate()
            # Wake the server up, so it doesn't wait for its select() timeout before terminating.
            # Just connecting does that: Sending anything, even no data, would fail with EPIPE if
            # the server accepted the connection and closed it on terminating in the meantime.
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as event_socket:
                event_socket.connect(str(settings.paths.event_socket.value))
            event_server.join(_TERMINATE_TIMEOUT)
        if event_server.is_alive():
            pytest.fail(f"the event server doesn't terminate within {_TERMINATE_TIMEOUT} s")
        # The event server closes the event pipe when it terminates, so it doesn't leak.
        if fds := _fds_open_on(settings.paths.event_pipe.value):
            pytest.fail(f"the event pipe is still open {fds} times after terminating")
        # The Event Console copes with failing queries itself, so don't let a test rely on that.
        if core.unexpected_queries:
            pytest.fail(f"unexpected Livestatus queries: {core.unexpected_queries!r}")


def _write_to_event_pipe(settings: ec.Settings, data: bytes) -> None:
    with settings.paths.event_pipe.value.open("wb") as pipe:
        pipe.write(data)


def _send_to_event_socket(settings: ec.Settings, data: bytes) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as event_socket:
        event_socket.connect(str(settings.paths.event_socket.value))
        event_socket.sendall(data)


def _event_texts(event_status: EventStatus) -> list[str]:
    with event_status.lock:
        return [event["text"] for event in event_status.events()]


def _texts_of_events(event_status: EventStatus, count: int) -> list[str]:
    """
    Returns the texts of the events once there are as many as given, or after a timeout, including
    surplus events coming right after them
    """
    deadline = time.monotonic() + _RECEIVE_TIMEOUT
    while len(_event_texts(event_status)) < count and time.monotonic() < deadline:
        time.sleep(0.01)
    time.sleep(_SURPLUS_EVENTS_TIMEOUT)
    return _event_texts(event_status)


def test_octet_counted_syslog_message_from_the_event_socket_is_not_split_at_its_newlines(
    event_console: _EventConsole,
) -> None:
    # Like the syslog exporter of the OpenTelemetry collector sends a multi-line log message
    message = b"<14>1 2026-11-02T16:00:00Z myservice myapp - - - disk \nfull\n"

    _send_to_event_socket(event_console.settings, b"%d %s" % (len(message), message))

    # The Event Console removes the newlines from the text, see scrub_string().
    assert _texts_of_events(event_console.event_status, 1) == ["disk full"]


def test_wrong_octet_count_on_the_event_pipe_holds_back_no_message_of_another_program(
    event_console: _EventConsole,
) -> None:
    settings, event_status = event_console
    # Like an octet-counted syslog message, but shorter than announced
    _write_to_event_pipe(settings, b"999 <14>not as long as announced\n")

    _write_to_event_pipe(settings, b"from another program\n")

    assert _texts_of_events(event_status, 2) == [
        "999 <14>not as long as announced",
        "from another program",
    ]


def _fds_open_on(path: Path) -> int:
    """Counts the file descriptors of this process which are open on the given file"""
    targets = []
    for fd in Path("/proc/self/fd").iterdir():
        with contextlib.suppress(FileNotFoundError):  # closed in the meantime
            targets.append(os.readlink(fd))
    return targets.count(str(path.resolve()))


def _make_adding_history_entries_fail(settings: ec.Settings) -> None:
    history_dir = settings.paths.history_dir.value
    # A file instead of the history directory makes adding entries fail, even for root.
    history_dir.parent.mkdir(parents=True, exist_ok=True)
    history_dir.touch()


def _restart_event_server_by_an_error(settings: ec.Settings, event_status: EventStatus) -> None:
    """
    Makes adding history entries fail, which restarts the event server with a raw history, and
    waits until the restarted event server has read a message from the event pipe
    """
    _make_adding_history_entries_fail(settings)
    _write_to_event_pipe(settings, b"before the restart\n")
    _texts_of_events(event_status, 1)  # The event is there before adding its entry fails.
    _write_to_event_pipe(settings, b"after the restart\n")
    if (texts := _texts_of_events(event_status, 2)) != ["before the restart", "after the restart"]:
        pytest.fail(f"no event from the event pipe after the restart: {texts!r}")


def test_event_server_restarted_after_an_error_has_the_event_pipe_open_only_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # The raw history raises its errors, which restarts the event server.
    with _running_event_console(create_history_raw) as (settings, event_status):
        _restart_event_server_by_an_error(settings, event_status)
        fds = _fds_open_on(settings.paths.event_pipe.value)

    assert "Exception in EventServer server" in caplog.text
    assert fds == 1


def test_event_server_restarted_after_an_error_keeps_the_start_of_a_message_from_the_event_pipe(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # The raw history raises its errors, which restarts the event server.
    with _running_event_console(create_history_raw) as (settings, event_status):
        _make_adding_history_entries_fail(settings)
        _write_to_event_pipe(settings, b"before the restart\nthe start of a message")
        _texts_of_events(event_status, 1)  # The event is there before adding its entry fails.

        _write_to_event_pipe(settings, b" and its rest\n")
        texts = _texts_of_events(event_status, 2)

    assert "Exception in EventServer server" in caplog.text
    assert texts == ["before the restart", "the start of a message and its rest"]


def test_event_server_restarted_after_an_error_keeps_a_client_with_the_start_of_its_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # The raw history raises its errors, which restarts the event server.
    with (
        _running_event_console(create_history_raw) as (settings, event_status),
        socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client,
    ):
        client.connect(str(settings.paths.event_socket.value))
        _make_adding_history_entries_fail(settings)
        client.sendall(b"before the restart\nthe start of a message")
        _texts_of_events(event_status, 1)  # The event is there before adding its entry fails.

        client.sendall(b" and its rest\n")
        texts = _texts_of_events(event_status, 2)

    assert "Exception in EventServer server" in caplog.text
    assert texts == ["before the restart", "the start of a message and its rest"]

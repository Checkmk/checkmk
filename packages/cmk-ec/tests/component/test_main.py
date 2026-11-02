#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import socket
import tempfile
import time
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import NamedTuple

import pytest

import cmk.ec.export as ec
from cmk.ccc.site import SiteId
from cmk.ec.helpers import ECLock
from cmk.ec.main import (
    create_history,
    default_slave_status_master,
    EventServer,
    EventStatus,
    make_config,
    StatusTableEvents,
    StatusTableHistory,
)
from cmk.ec.perfcounters import Perfcounters
from cmk.ec.settings import create_settings

_RECEIVE_TIMEOUT = 10  # seconds
_TERMINATE_TIMEOUT = 10  # seconds
# How long to wait for events beyond the expected ones, so a test sees surplus events, too
_SURPLUS_EVENTS_TIMEOUT = 0.1  # seconds

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


@pytest.fixture(name="event_console")
def fixture_event_console() -> Iterator[_EventConsole]:
    """A running event server, wired up like by main(), opening an event for each message"""
    # Unix socket paths are limited to ~108 bytes, which pytest's tmp_path may exceed.
    with tempfile.TemporaryDirectory(dir="/tmp") as omd_root:
        settings = create_settings("1.2.3i45", Path(omd_root), ["mkeventd"])
        settings.paths.event_pipe.value.parent.mkdir(parents=True)
        logger = logging.getLogger("cmk.mkeventd")
        # Unlike SQLite, recording the history in files leaves nothing open after the test.
        config = make_config(ec.default_config()) | {"archive_mode": "file"}
        history = create_history(
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

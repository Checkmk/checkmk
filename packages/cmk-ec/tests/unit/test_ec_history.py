#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import logging
import os
import sqlite3
from collections.abc import Iterable, Sequence
from typing import override

import pytest

import cmk.ec.export as ec
from cmk.ec.config import Config
from cmk.ec.history import ErrorLoggingHistory, History, HistoryWhat
from cmk.ec.main import EventServer, EventStatus, StatusServer
from cmk.ec.query import QueryGET

from .helpers import new_event, query_status_server


class _HistoryOnDisk(History):
    """Adds no entries while its disk fails with an error number"""

    def __init__(self) -> None:
        self.failure: int | None = None

    @override
    def flush(self) -> None:
        pass

    @override
    def add(self, event: ec.Event, what: HistoryWhat, who: str = "", addinfo: str = "") -> None:
        if self.failure is not None:
            raise OSError(self.failure, os.strerror(self.failure))

    @override
    def get(self, query: QueryGET) -> Iterable[Sequence[object]]:
        return []

    @override
    def housekeeping(self) -> None:
        pass

    @override
    def close(self) -> None:
        pass


_SQLITE_MESSAGES = {
    sqlite3.SQLITE_BUSY: "database is locked",
    sqlite3.SQLITE_FULL: "database or disk is full",
}


class _HistoryInSQLite(_HistoryOnDisk):
    """Adds no entries while SQLite fails with a result code"""

    @override
    def add(self, event: ec.Event, what: HistoryWhat, who: str = "", addinfo: str = "") -> None:
        if self.failure is not None:
            # Like sqlite3 raises an error for a result code of SQLite
            error = sqlite3.OperationalError(_SQLITE_MESSAGES[self.failure])
            error.sqlite_errorcode = self.failure
            raise error


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture(name="history_on_disk")
def fixture_history_on_disk() -> _HistoryOnDisk:
    return _HistoryOnDisk()


@pytest.fixture(name="clock")
def fixture_clock() -> _Clock:
    return _Clock()


@pytest.fixture(name="history")
def fixture_history(history_on_disk: _HistoryOnDisk, clock: _Clock) -> History:
    """The history on disk, logging the errors of adding entries like the history of main()"""
    return ErrorLoggingHistory(
        history_on_disk, logging.getLogger("cmk.mkeventd"), debug=False, clock=clock
    )


_EVENT = ec.Event(id=42, text="disk full")
_DISK_FULL = f"[Errno {errno.ENOSPC}] {os.strerror(errno.ENOSPC)}"
_IO_ERROR = f"[Errno {errno.EIO}] {os.strerror(errno.EIO)}"


def _logged(caplog: pytest.LogCaptureFixture) -> list[tuple[str, bool]]:
    """The messages logged, each with whether it comes with a stack trace"""
    return [(record.getMessage(), bool(record.exc_info)) for record in caplog.records]


def test_first_error_adding_a_history_entry_is_logged_with_a_stack_trace(
    history_on_disk: _HistoryOnDisk, history: History, caplog: pytest.LogCaptureFixture
) -> None:
    history_on_disk.failure = errno.ENOSPC

    history.add(_EVENT, "NEW")

    assert _logged(caplog) == [
        (f"Cannot add the NEW entry of event 42 to the history: {_DISK_FULL}", True)
    ]


def test_error_adding_a_history_entry_is_raised_in_debug_mode(
    history_on_disk: _HistoryOnDisk, clock: _Clock
) -> None:
    history = ErrorLoggingHistory(
        history_on_disk, logging.getLogger("cmk.mkeventd"), debug=True, clock=clock
    )
    history_on_disk.failure = errno.ENOSPC

    with pytest.raises(OSError) as excinfo:
        history.add(_EVENT, "NEW")

    assert excinfo.value.errno == errno.ENOSPC


def test_error_adding_history_entries_which_keeps_happening_is_reminded_of_once_a_minute(
    history_on_disk: _HistoryOnDisk,
    clock: _Clock,
    history: History,
    caplog: pytest.LogCaptureFixture,
) -> None:
    history_on_disk.failure = errno.ENOSPC
    history.add(_EVENT, "NEW")
    caplog.clear()

    for now in (30.0, 60.0, 90.0, 120.0):
        clock.now = now
        history.add(_EVENT, "NEW")

    assert _logged(caplog) == [
        (f"Still cannot add entries to the history, 3 missing so far: {_DISK_FULL}", False),
        (f"Still cannot add entries to the history, 5 missing so far: {_DISK_FULL}", False),
    ]


def test_another_kind_of_error_adding_history_entries_is_logged_once_with_a_stack_trace(
    history_on_disk: _HistoryOnDisk, history: History, caplog: pytest.LogCaptureFixture
) -> None:
    history_on_disk.failure = errno.ENOSPC
    history.add(_EVENT, "NEW")
    caplog.clear()

    history_on_disk.failure = errno.EIO
    history.add(_EVENT, "DELETE")
    history_on_disk.failure = errno.ENOSPC
    history.add(_EVENT, "NEW")
    history_on_disk.failure = errno.EIO
    history.add(_EVENT, "DELETE")

    assert _logged(caplog) == [
        (f"Cannot add the DELETE entry of event 42 to the history: {_IO_ERROR}", True)
    ]


def test_sqlite_error_with_another_result_code_adding_history_entries_is_logged_with_a_stack_trace(
    clock: _Clock, caplog: pytest.LogCaptureFixture
) -> None:
    history_in_sqlite = _HistoryInSQLite()
    history = ErrorLoggingHistory(
        history_in_sqlite, logging.getLogger("cmk.mkeventd"), debug=False, clock=clock
    )
    history_in_sqlite.failure = sqlite3.SQLITE_BUSY
    history.add(_EVENT, "NEW")
    caplog.clear()

    history_in_sqlite.failure = sqlite3.SQLITE_FULL
    history.add(_EVENT, "DELETE")

    assert _logged(caplog) == [
        ("Cannot add the DELETE entry of event 42 to the history: database or disk is full", True)
    ]


def test_adding_history_entries_working_again_logs_how_many_are_missing(
    history_on_disk: _HistoryOnDisk, history: History, caplog: pytest.LogCaptureFixture
) -> None:
    history_on_disk.failure = errno.ENOSPC
    history.add(_EVENT, "NEW")
    history.add(_EVENT, "DELETE")
    caplog.clear()

    history_on_disk.failure = None
    history.add(_EVENT, "NEW")

    assert _logged(caplog) == [
        ("Adding entries to the history works again, 2 entries are missing", False)
    ]


def test_error_adding_a_history_entry_after_it_worked_again_is_logged_with_a_stack_trace(
    history_on_disk: _HistoryOnDisk, history: History, caplog: pytest.LogCaptureFixture
) -> None:
    history_on_disk.failure = errno.ENOSPC
    history.add(_EVENT, "NEW")
    history_on_disk.failure = None
    history.add(_EVENT, "NEW")
    caplog.clear()

    history_on_disk.failure = errno.ENOSPC
    history.add(_EVENT, "DELETE")

    assert _logged(caplog) == [
        (f"Cannot add the DELETE entry of event 42 to the history: {_DISK_FULL}", True)
    ]


def test_closing_the_history_after_errors_adding_entries_logs_how_many_are_missing(
    history_on_disk: _HistoryOnDisk, history: History, caplog: pytest.LogCaptureFixture
) -> None:
    history_on_disk.failure = errno.ENOSPC
    history.add(_EVENT, "NEW")
    history.add(_EVENT, "DELETE")
    caplog.clear()

    history.close()

    assert _logged(caplog) == [
        ("Closing the history after errors adding entries, 2 entries are missing", False)
    ]


def test_each_error_adding_a_history_entry_after_closing_the_history_is_logged(
    history_on_disk: _HistoryOnDisk, history: History, caplog: pytest.LogCaptureFixture
) -> None:
    history.close()
    history_on_disk.failure = errno.ENOSPC

    history.add(_EVENT, "NEW")
    history.add(_EVENT, "DELETE")

    assert _logged(caplog) == [
        (f"Cannot add the NEW entry of event 42 to the closed history: {_DISK_FULL}", False),
        (f"Cannot add the DELETE entry of event 42 to the closed history: {_DISK_FULL}", False),
    ]


def test_command_is_answered_although_adding_its_history_entry_fails(
    history_on_disk: _HistoryOnDisk, event_status: EventStatus, status_server: StatusServer
) -> None:
    event_status.new_event(new_event(ec.Event(text="disk full")))
    history_on_disk.failure = errno.ENOSPC

    status_socket = query_status_server(status_server, "COMMAND UPDATE;1;harry;1;;")

    assert status_socket.get_raw_response() == b"None\n"


def test_deleted_event_no_longer_counts_for_the_limits_although_adding_its_history_entry_fails(
    config: Config,
    history_on_disk: _HistoryOnDisk,
    history: History,
    event_server: EventServer,
    event_status: EventStatus,
    status_server: StatusServer,
) -> None:
    event_limit = config["event_limit"] | {"overall": ec.EventLimit(action="stop", limit=1)}
    event_server.reload_configuration(config | {"event_limit": event_limit}, history)
    event_status.new_event(new_event(ec.Event(text="disk full")))
    history_on_disk.failure = errno.ENOSPC

    query_status_server(status_server, "COMMAND DELETE;1;harry")

    assert not event_server.is_overall_event_limit_active()


def test_removed_event_no_longer_counts_for_the_limits_although_adding_its_history_entry_raises(
    config: Config,
    history_on_disk: _HistoryOnDisk,
    event_server: EventServer,
    event_status: EventStatus,
) -> None:
    # Like the history in debug mode, the history on disk raises its errors.
    event_limit = config["event_limit"] | {"overall": ec.EventLimit(action="stop", limit=1)}
    limited_config = config | {"event_limit": event_limit}
    event_server.reload_configuration(limited_config, history_on_disk)
    event_status.reload_configuration(limited_config, history_on_disk)
    event = new_event(ec.Event(text="disk full"))
    event_status.new_event(event)
    history_on_disk.failure = errno.ENOSPC

    with pytest.raises(OSError):
        event_status.remove_event(event, "DELETE")

    assert not event_server.is_overall_event_limit_active()

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from logging import Logger
from pathlib import Path
from typing import Literal, override

from .config import Config
from .event import Event
from .query import QueryGET

HistoryWhat = Literal[
    "ORPHANED",
    "NOCOUNT",
    "DELAYOVER",
    "EXPIRED",
    "COUNTREACHED",
    "COUNTFAILED",
    "UPDATE",
    "NEW",
    "DELETE",
    "EMAIL",
    "SCRIPT",
    "CANCELLED",
    "ARCHIVED",
    "AUTODELETE",
    "CHANGESTATE",
]


class History(ABC):
    @abstractmethod
    def flush(self) -> None: ...

    @abstractmethod
    def add(self, event: Event, what: HistoryWhat, who: str = "", addinfo: str = "") -> None: ...

    @abstractmethod
    def get(self, query: QueryGET) -> Iterable[Sequence[object]]: ...

    @abstractmethod
    def housekeeping(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


class TimedHistory(History):
    """Decorate History methods with timing information."""

    def __init__(self, history: History, logger: Logger) -> None:
        self._history = history
        self._logger = logger

    @contextmanager
    def _timing(self, method_name: str) -> Iterator[None]:
        tic = time.time()
        try:
            yield
        finally:
            self._logger.debug(
                "history method call '%(method_name)s' took %(duration_ms).3f ms",
                {"method_name": method_name, "duration_ms": (time.time() - tic) * 1000},
            )

    @override
    def flush(self) -> None:
        with self._timing("flush"):
            self._history.flush()

    @override
    def housekeeping(self) -> None:
        with self._timing("housekeeping"):
            self._history.housekeeping()

    @override
    def add(self, event: Event, what: HistoryWhat, who: str = "", addinfo: str = "") -> None:
        with self._timing("add"):
            self._history.add(event, what, who, addinfo)

    @override
    def get(self, query: QueryGET) -> Iterable[Sequence[object]]:
        with self._timing("get"):
            return self._history.get(query)

    @override
    def close(self) -> None:
        with self._timing("close"):
            return self._history.close()


# The least time between two reminders of errors adding history entries which keep happening
_REMINDER_INTERVAL = 60.0  # seconds

type _KindOfError = tuple[type[Exception], int | None]


def _kind_of_error(error: Exception) -> _KindOfError:
    """
    Its type, and for an OSError its number and for an SQLite error its result code, e.g. to tell a
    locked database from a full disk, but not its message, which may change with each try for the
    same cause, e.g. for an unreachable MongoDB
    """
    match error:
        case OSError():
            return type(error), error.errno
        case _:
            # Looked up by name, so the other history backends don't need to import sqlite3. And
            # sqlite3 raises some errors itself, without a result code, e.g. for a closed database.
            return type(error), getattr(error, "sqlite_errorcode", None)


class ErrorLoggingHistory(History):
    """Decorate History.add() to log its errors instead of raising them.

    Processing an event shouldn't fail because its history entry can't be written, e.g. on a full
    disk: Its rule's actions would be skipped, and the event server would restart.

    So that e.g. an unreachable database doesn't flood the log, it logs a series of such errors
    briefly: Each kind of error once with a stack trace, then at most every _REMINDER_INTERVAL a
    reminder with the number of entries missing so far, and their final number once adding entries
    works again or the history is closed. After closing, nothing ends a series anymore, so it logs
    each error on its own.

    In debug mode, it raises the errors, like the rest of the Event Console does.
    """

    def __init__(
        self,
        history: History,
        logger: Logger,
        *,
        debug: bool,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._history = history
        self._logger = logger
        self._debug = debug
        # Only tests pass a clock: Reminders use the monotonic clock, so that changing the system
        # time doesn't affect them, and time_machine can't fake that one.
        self._clock = clock
        # Several threads add entries, e.g. the event server and the status server.
        self._lock = threading.Lock()
        # The current series of errors, i.e. since adding an entry failed after it worked
        self._kinds_of_errors: set[_KindOfError] = set()
        self._missing = 0
        self._next_reminder = 0.0
        # Only what was under way while reloading the configuration still adds entries afterwards.
        self._closed = False

    @override
    def flush(self) -> None:
        self._history.flush()

    @override
    def housekeeping(self) -> None:
        self._history.housekeeping()

    @override
    def add(self, event: Event, what: HistoryWhat, who: str = "", addinfo: str = "") -> None:
        try:
            self._history.add(event, what, who, addinfo)
        except Exception as e:
            if self._debug:
                raise
            self._log_error(event, what, e)
        else:
            # Without errors, the usual case, take the lock only to end a series of them.
            if self._missing and (missing := self._end_errors()):
                self._logger.warning(
                    "Adding entries to the history works again, %(missing)d entries are missing",
                    {"missing": missing},
                )

    def _log_error(self, event: Event, what: HistoryWhat, error: Exception) -> None:
        with self._lock:
            if self._closed:
                self._logger.error(
                    "Cannot add the %(what)s entry of event %(event_id)s to the closed history: "
                    "%(error)s",
                    {"what": what, "event_id": event.get("id"), "error": error},
                )
                return
            self._missing += 1
            now = self._clock()
            if (kind := _kind_of_error(error)) not in self._kinds_of_errors:
                self._kinds_of_errors.add(kind)
                self._logger.error(
                    "Cannot add the %(what)s entry of event %(event_id)s to the history: %(error)s",
                    {"what": what, "event_id": event.get("id"), "error": error},
                    exc_info=error,
                )
            elif now >= self._next_reminder:
                self._logger.error(
                    "Still cannot add entries to the history, %(missing)d missing so far: %(error)s",
                    {"missing": self._missing, "error": error},
                )
            else:
                return
            self._next_reminder = now + _REMINDER_INTERVAL

    def _end_errors(self) -> int:
        """Ends the current series of errors, returning the number of entries missing by it"""
        with self._lock:
            missing, self._missing = self._missing, 0
            self._kinds_of_errors.clear()
            return missing

    @override
    def get(self, query: QueryGET) -> Iterable[Sequence[object]]:
        return self._history.get(query)

    @override
    def close(self) -> None:
        with self._lock:
            self._closed = True
        if missing := self._end_errors():
            self._logger.warning(
                "Closing the history after errors adding entries, %(missing)d entries are missing",
                {"missing": missing},
            )
        self._history.close()


def _log_event(
    config: Config, logger: Logger, event: Event, what: HistoryWhat, who: str, addinfo: str
) -> None:
    if config["debug_rules"]:
        logger.info(
            "Event %(event_id)d: %(what)s/%(who)s/%(addinfo)s - %(text)s",
            {
                "event_id": event["id"],
                "what": what,
                "who": who,
                "addinfo": addinfo,
                "text": event["text"],
            },
        )


def quote_tab(col: object) -> bytes:
    if isinstance(col, bool):
        return b"1" if col else b"0"
    if isinstance(col, float | int):
        return str(col).encode("utf-8")
    if isinstance(col, tuple | list):
        return b"\1" + b"\1".join(quote_tab(e) for e in col)
    if col is None:
        return b"\2"
    if isinstance(col, str):
        col = col.encode("utf-8")
    assert isinstance(col, bytes)
    return col.replace(b"\t", b" ")


class ActiveHistoryPeriod:
    def __init__(self) -> None:
        self.value: int | None = None


def get_logfile(config: Config, log_dir: Path, active_history_period: ActiveHistoryPeriod) -> Path:
    """Get file object to current log file, handle also history and lifetime limit."""
    log_dir.mkdir(parents=True, exist_ok=True)
    # Log into file starting at current history period,
    # but: if a newer logfile exists, use that one. This
    # can happen if you switch the period from daily to
    # weekly.
    timestamp = _current_history_period(config)

    # Log period has changed or we have not computed a filename yet ->
    # compute currently active period
    if active_history_period.value is None or timestamp > active_history_period.value:
        # Look if newer files exist
        timestamps = sorted(int(path.stem) for path in log_dir.glob("*.log"))
        if len(timestamps) > 0:
            timestamp = max(timestamps[-1], timestamp)

        active_history_period.value = timestamp

    return log_dir / f"{timestamp}.log"


def _current_history_period(config: Config) -> int:
    """Return timestamp of the beginning of the current history period."""
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    return int(
        (
            today
            - datetime.datetime(1970, 1, 1)
            - datetime.timedelta(
                days=today.weekday() if config["history_rotation"] == "weekly" else 0
            )
        ).total_seconds()
    )

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import time
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from logging import getLogger, Logger
from pathlib import Path
from typing import Any, Literal

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

    def __init__(self, history: History) -> None:
        self._history = history
        self._logger = getLogger("cmk.mkeventd")

    @contextmanager
    def _timing(self, method_name: str) -> Iterator[None]:
        tic = time.time()
        try:
            yield
        finally:
            self._logger.debug(
                "method call %s took: %.3f ms", method_name, (time.time() - tic) * 1000
            )

    def flush(self) -> None:
        with self._timing("flush"):
            self._history.flush()

    def housekeeping(self) -> None:
        with self._timing("housekeeping"):
            self._history.housekeeping()

    def add(self, event: Event, what: HistoryWhat, who: str = "", addinfo: str = "") -> None:
        with self._timing("add"):
            self._history.add(event, what, who, addinfo)

    def get(self, query: QueryGET) -> Iterable[Sequence[object]]:
        with self._timing("get"):
            return self._history.get(query)

    def close(self) -> None:
        with self._timing("close"):
            return self._history.close()


def _log_event(
    config: Config, logger: Logger, event: Event, what: HistoryWhat, who: str, addinfo: str
) -> None:
    if config["debug_rules"]:
        logger.info("Event %d: %s/%s/%s - %s", event["id"], what, who, addinfo, event["text"])


def quote_tab(col: Any) -> bytes:
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

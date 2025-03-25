#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
import shlex
import subprocess
import threading
import time
from collections.abc import Callable, Iterable, Sequence
from logging import Logger
from pathlib import Path
from typing import Any

from cmk.utils.log import VERBOSE
from cmk.utils.render import date_and_time

from .config import Config
from .event import Event, scrub_string
from .history import _log_event, ActiveHistoryPeriod, get_logfile, History, HistoryWhat, quote_tab
from .query import Columns, OperatorName, QueryFilter, QueryGET
from .settings import Settings


class FileHistory(History):
    def __init__(
        self,
        settings: Settings,
        config: Config,
        logger: Logger,
        event_columns: Columns,
        history_columns: Columns,
    ) -> None:
        self._settings = settings
        self._config = config
        self._logger = logger
        self._event_columns = event_columns
        self._history_columns = history_columns
        self._lock = threading.Lock()
        self._active_history_period = ActiveHistoryPeriod()

    def flush(self) -> None:
        _expire_logfiles(self._settings, self._config, self._logger, self._lock, True)

    def add(self, event: Event, what: HistoryWhat, who: str = "", addinfo: str = "") -> None:
        """Make a new entry in the event history.

        Each entry is tab-separated line with the following columns:
        0: time of log entry
        1: type of entry (keyword)
        2: user who initiated the action (for GUI actions)
        3: additional information about the action
        4-oo: StatusTableEvents.columns
        """
        _log_event(self._config, self._logger, event, what, who, addinfo)
        with self._lock:
            columns = [
                quote_tab(str(time.time())),
                quote_tab(scrub_string(what)),
                quote_tab(scrub_string(who)),
                quote_tab(scrub_string(addinfo)),
            ]
            columns += [
                quote_tab(event.get(colname[6:], defval))  # drop "event_"
                for colname, defval in self._event_columns
            ]

            with get_logfile(
                self._config,
                self._settings.paths.history_dir.value,
                self._active_history_period,
            ).open(mode="ab") as f:
                f.write(b"\t".join(columns) + b"\n")

    def get(self, query: QueryGET) -> Iterable[Sequence[object]]:
        if not self._settings.paths.history_dir.value.exists():
            return []

        filters = query.filters
        self._logger.debug("Filters: %r", filters)
        limit = query.limit
        self._logger.debug("Limit: %r", limit)

        grep_pipeline = _grep_pipeline(filters)

        time_filters = [
            (f.operator_name, f.argument) for f in filters if f.column_name.split("_")[-1] == "time"
        ]
        time_range = (
            _greatest_lower_bound_for_filters(time_filters),
            _least_upper_bound_for_filters(time_filters),
        )
        self._logger.debug("time range: %r", time_range)

        # We do not want to open all files. So our strategy is:
        # look for "time" filters and first apply the filter to
        # the first entry and modification time of the file. Only
        # if at least one of both timestamps is accepted then we
        # take that file into account.
        # Use the later logfiles first, to get the newer log entries
        # first. When a limit is reached, the newer entries should
        # be processed in most cases. We assume that now.
        # To keep a consistent order of log entries, we should care
        # about sorting the log lines in reverse, but that seems to
        # already be done by the GUI, so we don't do that twice. Skipping
        # this # will lead into some lines of a single file to be limited in
        # wrong order. But this should be better than before.
        history_entries: list[Any] = []
        for path in sorted(self._settings.paths.history_dir.value.glob("*.log"), reverse=True):
            if limit is not None and limit <= 0:
                self._logger.debug("query limit reached")
                break
            if not _intersects(time_range, _get_logfile_timespan(path)):
                self._logger.debug("skipping history file %s because of time filters", path)
                continue
            tac = f"nl -b a {shlex.quote(str(path))} | tac"  # Process younger lines first
            cmd = " | ".join([tac] + grep_pipeline)
            self._logger.debug("preprocessing history file with command [%s]", cmd)
            new_entries = parse_history_file(
                self._history_columns, path, query.filter_row, cmd, limit, self._logger
            )
            history_entries += new_entries
            if limit is not None:
                limit -= len(new_entries)
        return history_entries

    def housekeeping(self) -> None:
        _expire_logfiles(self._settings, self._config, self._logger, self._lock, False)

    def close(self) -> None:
        pass


def _expire_logfiles(
    settings: Settings, config: Config, logger: Logger, lock_history: threading.Lock, flush: bool
) -> None:
    """Delete old log files."""
    with lock_history:
        try:
            days = config["history_lifetime"]
            min_mtime = time.time() - days * 86400
            logger.log(
                VERBOSE,
                "Expiring logfiles (Horizon: %d days -> %s)",
                days,
                date_and_time(min_mtime),
            )
            for path in settings.paths.history_dir.value.glob("*.log"):
                if flush or path.stat().st_mtime < min_mtime:
                    logger.info(
                        "Deleting log file %s (age %s)", path, date_and_time(path.stat().st_mtime)
                    )
                    path.unlink()
        except Exception as e:
            if settings.options.debug:
                raise
            logger.warning("Error expiring log files: %s", e)


# Please note: Keep this in sync with packages/neb/src/TableEventConsole.cc.
_GREPABLE_COLUMNS = {
    "event_id",
    "event_text",
    "event_comment",
    "event_host",
    "event_contact",
    "event_application",
    "event_rule_id",
    "event_owner",
    "event_ipaddress",
    "event_core_host",
}


def _grep_pipeline(filters: Iterable[QueryFilter]) -> list[str]:
    """
    Optimization: use grep in order to reduce amount of read lines based on some frequently used
    filters. It's OK if the filters don't match 100% accurately on the right lines. If in doubt, you
    can output more lines than necessary. This is only a kind of prefiltering.

    >>> _grep_pipeline([])
    []

    >>> _grep_pipeline([QueryFilter("event_core_host", '=', lambda x: True, '|| ping')])
    ["grep -F -e '|| ping'"]

    """
    return [
        command
        for f in filters
        if f.column_name in _GREPABLE_COLUMNS
        for command in [_grep_command(f.operator_name, str(f.argument))]
        if command is not None
    ]


def _grep_command(operator_name: OperatorName, argument: str) -> str | None:
    if operator_name == "=":
        return f"grep -F {_grep_pattern(argument)}"
    if operator_name == "=~":
        return f"grep -F -i {_grep_pattern(argument)}"
    if operator_name == "~":
        return f"grep -E {_grep_pattern(argument)}"
    if operator_name == "~~":
        return f"grep -E -i {_grep_pattern(argument)}"
    return None


def _grep_pattern(argument: str) -> str:
    return f"-e {shlex.quote(argument)}"


def _greatest_lower_bound_for_filters(
    filters: Iterable[tuple[OperatorName, float]],
) -> float | None:
    result: float | None = None
    for operator, value in filters:
        glb = _greatest_lower_bound_for_filter(operator, value)
        if glb is not None:
            result = glb if result is None else max(result, glb)
    return result


def _greatest_lower_bound_for_filter(operator: OperatorName, value: float) -> float | None:
    if operator == "=":
        return value
    if operator == ">=":
        return value
    if operator == ">":
        return value + 1
    return None


def _least_upper_bound_for_filters(filters: Iterable[tuple[OperatorName, float]]) -> float | None:
    result: float | None = None
    for operator, value in filters:
        lub = _least_upper_bound_for_filter(operator, value)
        if lub is not None:
            result = lub if result is None else min(result, lub)
    return result


def _least_upper_bound_for_filter(operator: OperatorName, value: float) -> float | None:
    if operator == "=":
        return value
    if operator == "<=":
        return value
    if operator == "<":
        return value - 1
    return None


def _intersects(
    interval1: tuple[float | None, float | None],
    interval2: tuple[float | None, float | None],
) -> bool:
    lo1, hi1 = interval1
    lo2, hi2 = interval2
    return (lo2 is None or hi1 is None or lo2 <= hi1) and (lo1 is None or hi2 is None or lo1 <= hi2)


def parse_history_file(
    history_columns: Sequence[tuple[str, Any]],
    path: Path,
    filter_row: Callable[[Sequence[Any]], bool],
    cmd: str,
    limit: int | None,
    logger: Logger,
) -> list[Any]:
    entries: list[Any] = []
    with subprocess.Popen(
        cmd,
        shell=True,  # nosec B602 # BNS:67522a
        close_fds=True,
        stdout=subprocess.PIPE,
    ) as grep:
        if grep.stdout is None:
            raise Exception("Huh? stdout vanished...")

        for line in grep.stdout:
            if limit is not None and len(entries) > limit:
                break
            try:
                parts: list[Any] = line.decode("utf-8").rstrip("\n").split("\t")
                convert_history_line(history_columns, parts)
                if filter_row(parts):
                    entries.append(parts)
            except Exception:
                logger.exception("Invalid line '%s' in history file %s", line, path)

    return entries


def parse_history_file_python(
    history_columns: Sequence[tuple[str, Any]],
    path: Path,
    logger: Logger,
) -> Iterable[Sequence[Any]]:
    """Pure python reader for history files. Used for update config, where filtering is not needed.

    To avoid slurping the whole file in memory this generator yields chunks of entries.
    This is not faster than the grep approach(parse_history_file()), but it's more memory efficient
    and does not need to fork a subprocess and other cmk specific stuff.
    """
    with open(path, "rb") as f:
        for chunk in itertools.batched(f, 100_000):
            entries = []
            for line in chunk:
                try:
                    parts: list[Any] = line.decode("utf-8").rstrip("\n").split("\t")
                    parts.insert(0, 0)  # add line number
                    convert_history_line(history_columns, parts)
                    entries.append(parts)
                except Exception:
                    logger.exception("Invalid line '%s' in history file %s", line, path)
            yield entries


def convert_history_line(history_columns: Sequence[tuple[str, Any]], values: list[Any]) -> None:
    """
    Speed-critical function for converting string representation
    of log line back to Python values.
    """
    values[0] = int(values[0])  # history_line
    values[1] = float(values[1])  # history_time
    values[5] = int(values[5])  # event_id
    values[6] = int(values[6])  # event_count
    values[8] = float(values[8])  # event_first
    values[9] = float(values[9])  # event_last
    values[11] = int(values[11])  # event_sl
    values[15] = int(values[15])  # event_pid
    values[16] = int(values[16])  # event_priority
    values[17] = int(values[17])  # event_facility
    values[19] = int(values[19])  # event_state
    values[22] = _unsplit(values[22])  # event_match_groups
    num_values = len(values)
    if num_values <= 23:  # event_contact_groups
        values.append(None)
    else:
        values[23] = _unsplit(values[23])
    if num_values <= 24:  # event_ipaddress
        values.append(history_columns[25][1])
    if num_values <= 25:  # event_orig_host
        values.append(history_columns[26][1])
    if num_values <= 26:  # event_contact_groups_precedence
        values.append(history_columns[27][1])
    if num_values <= 27:  # event_core_host
        values.append(history_columns[28][1])
    if num_values <= 28:  # event_host_in_downtime
        values.append(history_columns[29][1])
    else:
        values[28] = values[28] == "1"
    if num_values <= 29:  # event_match_groups_syslog_application
        values.append(history_columns[30][1])
    else:
        values[29] = _unsplit(values[29])


def _unsplit(s: Any) -> Any:
    if not isinstance(s, str):
        return s
    if s.startswith("\2"):
        return None  # \2 is the designator for None
    if s.startswith("\1"):
        if len(s) == 1:
            return ()
        return tuple(s[1:].split("\1"))
    return s


def _get_logfile_timespan(path: Path) -> tuple[float | None, float | None]:
    try:
        with path.open(encoding="utf-8") as f:
            first_entry: float | None = float(f.readline().split("\t", 1)[0])
    except Exception:
        first_entry = None
    try:
        last_entry: float | None = path.stat().st_mtime
    except Exception:
        last_entry = None
    return first_entry, last_entry

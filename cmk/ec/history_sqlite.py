#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""EC History sqlite backend"""

import itertools
import sqlite3
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from logging import Logger
from pathlib import Path

from .config import Config
from .event import Event
from .history import History, HistoryWhat
from .query import Columns, QueryFilter, QueryGET
from .settings import Options, Paths, Settings


def history_file_to_sqlite(file: Path, connection: sqlite3.Connection) -> None:
    """
    Dumps a history file contents into a sqlite database in batches of 10k entries.

    Tested with 50Mb file with 140k entries took about 1.31s
    No need for connection.commit() for every 10k entries, since it will take about 6min for the same 50Mb file.
    """

    def __iter(serialized: Iterable[str]) -> Iterator[tuple[str]]:
        for entries in (line.strip().split("\t") for line in serialized):
            yield from itertools.batched(entries, 10000)

    with open(file, "r") as f, connection as con:
        cur = con.cursor()
        cur.executemany(
            """INSERT INTO history (time, what, who, addinfo, id, count, text, first, last,
                                comment, sl, host, contact, application,
                                pid, priority, facility, rule_id,
                                state, phase, owner, match_groups,
                                contact_groups, ipaddress, orig_host,
                                contact_groups_precedence, core_host, host_in_downtime,
                                match_groups_syslog_application)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
            __iter(f),
        )


def filters_to_sqlite_query(filters: Iterable[QueryFilter]) -> str:
    """
    Construct the sqlite filtering specification.

    Used in SQLiteHistory.get() method.
    """

    query_columns: set[str] = set()
    query_conditions: list[str] = []

    for f in filters:
        adjusted_column_name = ""

        if f.column_name.startswith("event_") or f.column_name.startswith("history_"):
            adjusted_column_name = f.column_name.replace("event_", "").replace("history_", "")
        else:
            raise ValueError(f"Filter {f.column_name} not implemented for SQLite")

        sqlite_filter: str = {
            "=": f"{adjusted_column_name} {f.operator_name} {f.argument}",
            ">": f"{adjusted_column_name} {f.operator_name} {f.argument}",
            "<": f"{adjusted_column_name} {f.operator_name} {f.argument}",
            ">=": f"{adjusted_column_name} {f.operator_name} {f.argument}",
            "<=": f"{adjusted_column_name} {f.operator_name} {f.argument}",
            "~": f"{adjusted_column_name} LIKE '%{f.argument}%'",
            "=~": f"{adjusted_column_name} LIKE '%{f.argument}%'",
            "~~": f"{adjusted_column_name} LIKE '%{f.argument}%'",
            "in": f"{adjusted_column_name} in '%{f.argument}%'",
        }[f.operator_name]

        query_columns.add(adjusted_column_name)
        query_conditions.append(sqlite_filter)

    return f'SELECT {", ".join(sorted(query_columns))} FROM history WHERE {" AND ".join(query_conditions)};'


@dataclass
class SQLiteSettings:
    paths: Paths
    options: Options
    database: str | Path

    @classmethod
    def from_settings(cls, settings: Settings, db: str | Path = "") -> "SQLiteSettings":
        return cls(
            paths=settings.paths,
            options=settings.options,
            database=db or Path(settings.paths.history_dir.value / "history.sqlite"),
        )


class SQLiteHistory(History):
    def __init__(
        self,
        settings: SQLiteSettings,
        config: Config,
        logger: Logger,
        event_columns: Columns,
        history_columns: Columns,
    ):
        self._settings = settings
        self._config = config
        self._logger = logger
        self._event_columns = event_columns
        self._history_columns = history_columns

        self.conn = sqlite3.connect(self._settings.database)

        self.cursor = self.conn.cursor()
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS history
                             (time text, what text, who text, addinfo text, id INTEGER, count INTEGER,
                             text TEXT, first FLOAT, last FLOAT,
                             comment TEXT, sl INTEGER, host TEXT, contact TEXT, application TEXT,
                             pid INTEGER, priority INTEGER, facility INTEGER, rule_id TEXT,
                             state INTEGER, phase TEXT, owner TEXT, match_groups TEXT,
                             contact_groups TEXT, ipaddress TEXT, orig_host TEXT,
                             contact_groups_precedence TEXT, core_host TEXT, host_in_downtime BOOL,
                             match_groups_syslog_application TEXT);"""
        )
        self.conn.commit()

    def flush(self) -> None:
        self.conn.execute("DROP TABLE IF EXISTS history;")
        self.conn.commit()

    def add(self, event: Event, what: HistoryWhat, who: str = "", addinfo: str = "") -> None:
        """
        docstring
        """

    def get(self, query: QueryGET) -> Iterable[Sequence[object]]:
        """
        docstring
        """
        return ()

    def housekeeping(self) -> None:
        """
        docstring
        """

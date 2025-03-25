#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""EC History sqlite backend."""

import itertools
import json
import sqlite3
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import timedelta
from logging import Logger
from pathlib import Path
from typing import Final, Literal

from .config import Config
from .event import Event
from .history import History, HistoryWhat
from .query import Columns, QueryFilter, QueryGET
from .settings import Options, Paths, Settings

TABLE_COLUMNS: Final = (
    "line",
    "time",
    "what",
    "who",
    "addinfo",
    "id",
    "count",
    "text",
    "first",
    "last",
    "comment",
    "sl",
    "host",
    "contact",
    "application",
    "pid",
    "priority",
    "facility",
    "rule_id",
    "state",
    "phase",
    "owner",
    "match_groups",
    "contact_groups",
    "ipaddress",
    "orig_host",
    "contact_groups_precedence",
    "core_host",
    "host_in_downtime",
    "match_groups_syslog_application",
)

INDEXED_COLUMNS: Final = (
    "time",
    "id",
    "host",
)

SQLITE_PRAGMAS = {
    "PRAGMA journal_mode=WAL;": "WAL mode for concurrent reads and writes",
    "PRAGMA synchronous = NORMAL;": "Writes should not blocked by reads",
    "PRAGMA busy_timeout = 2000;": "2 seconds timeout for busy handler. Avoids database is locked errors",
}

SQLITE_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{column} ON history ({column});" for column in INDEXED_COLUMNS
]


def configure_sqlite_types() -> None:
    """
    Registers the required converters/adaptors for the sqlite3 type conversions.

    Converter converts JSON to python objects(sqlite->python).

    Adaptor converts python objects to JSON(python->sqlite). E.g. list/tuple -> JSON string.
    """
    sqlite3.register_converter("JSON", lambda value: json.loads(value.decode("utf8")))
    sqlite3.register_converter("BOOL", lambda value: value.decode("utf8") == "1")

    sqlite3.register_adapter(bool, int)
    sqlite3.register_adapter(list, json.dumps)
    sqlite3.register_adapter(tuple, json.dumps)


def filters_to_sqlite_query(filters: Iterable[QueryFilter]) -> tuple[str, list[object]]:
    """
    Construct the sqlite filtering specification.

    Used in SQLiteHistory.get() method.
    Always return all columns, since they are filtered elsewhere.
    """
    query_columns: set[str] = set()
    query_conditions: list[str] = []
    query_arguments: list[object] = []

    for f in filters:
        adjusted_column_name = ""

        if f.column_name.startswith("event_") or f.column_name.startswith("history_"):
            adjusted_column_name = f.column_name.replace("event_", "").replace("history_", "")
        else:
            raise ValueError(f"Filter {f.column_name} not implemented for SQLite")

        if adjusted_column_name not in TABLE_COLUMNS:
            raise ValueError(f"Filter {f.column_name} not implemented for SQLite")

        sqlite_filter: str = {
            "=": f"{adjusted_column_name} {f.operator_name} ?",
            ">": f"{adjusted_column_name} {f.operator_name} ?",
            "<": f"{adjusted_column_name} {f.operator_name} ?",
            ">=": f"{adjusted_column_name} {f.operator_name} ?",
            "<=": f"{adjusted_column_name} {f.operator_name} ?",
            "~": f"{adjusted_column_name} LIKE '%?%'",
            "=~": f"{adjusted_column_name} LIKE '%?%'",
            "~~": f"{adjusted_column_name} LIKE '%?%'",
            "in": f"{adjusted_column_name} in '%?%'",
        }[f.operator_name]

        query_columns.add(adjusted_column_name)
        query_conditions.append(sqlite_filter)
        query_arguments.append(f.argument)
    return (
        f"SELECT * FROM history {'WHERE' if query_arguments else ''} {' AND '.join(query_conditions)};",  # nosec B608 # BNS:6b6392
        query_arguments,
    )


@dataclass
class SQLiteSettings:
    paths: Paths
    options: Options
    database: Literal[":memory:"] | Path

    @classmethod
    def from_settings(
        cls, settings: Settings, *, database: Literal[":memory:"] | Path
    ) -> "SQLiteSettings":
        return cls(paths=settings.paths, options=settings.options, database=database)


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
        self._last_housekeeping = 0.0
        self._page_size = 4096

        if isinstance(self._settings.database, Path):
            self._settings.database.parent.mkdir(parents=True, exist_ok=True)
            self._settings.database.touch(exist_ok=True)

        configure_sqlite_types()

        # TODO lookup our ec backend thread safety.
        # check_same_thread=False the connection may be accessed in multiple threads.
        self.conn = sqlite3.connect(
            self._settings.database, check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES
        )

        self.conn.row_factory = sqlite3.Row

        with self.conn as connection:
            for pragma_string in SQLITE_PRAGMAS:
                connection.execute(pragma_string)
            self._page_size = connection.execute("PRAGMA page_size").fetchone()[0]

        with self.conn as connection:
            cur = connection.cursor()
            cur.execute(
                """CREATE TABLE IF NOT EXISTS
                    history (
                        line INTEGER PRIMARY KEY AUTOINCREMENT,
                        time REAL,
                        what TEXT,
                        who TEXT,
                        addinfo TEXT,
                        id INTEGER,
                        count INTEGER,
                        text TEXT,
                        first REAL,
                        last REAL,
                        comment TEXT,
                        sl INTEGER,
                        host TEXT,
                        contact TEXT,
                        application TEXT,
                        pid INTEGER,
                        priority INTEGER,
                        facility INTEGER,
                        rule_id TEXT,
                        state INTEGER,
                        phase TEXT,
                        owner TEXT,
                        match_groups JSON,
                        contact_groups JSON,
                        ipaddress TEXT,
                        orig_host TEXT,
                        contact_groups_precedence TEXT,
                        core_host TEXT,
                        host_in_downtime BOOL,
                        match_groups_syslog_application JSON
                    );"""
            )
        with self.conn as connection:
            for index_statement in SQLITE_INDEXES:
                connection.execute(index_statement)

    def flush(self) -> None:
        """Delete all entries the history table."""
        with self.conn as connection:
            connection.execute("DELETE FROM history;")

    def add(self, event: Event, what: HistoryWhat, who: str = "", addinfo: str = "") -> None:
        """Add a single entry to the history table.

        No need to include the line column, as it is autoincremented.
        """
        with self.conn as connection:
            cur = connection.cursor()
            cur.execute(
                f"""INSERT INTO
                    history ({", ".join(TABLE_COLUMNS[1:])})
                        VALUES ({", ".join(itertools.repeat("?", len(TABLE_COLUMNS[1:])))});""",  # nosec B608 # BNS:6b6392
                tuple(
                    itertools.chain(
                        (time.time(), what, who, addinfo),
                        [
                            event.get(colname.removeprefix("event_"), defval)
                            for colname, defval in self._event_columns
                        ],
                    )
                ),
            )

    def add_entries(self, entries: Sequence[Sequence[object]]) -> None:
        """Add multiple entries to the history table.

        Used only by the cmk-update-config during EC history migration to sqlite.
        The first column is the line number, which is autoincremented, so ignored in TABLE_COLUMNS.
        """
        with self.conn as connection:
            cur = connection.cursor()
            cur.executemany(
                f"""INSERT INTO
                    history ({", ".join(TABLE_COLUMNS[1:])})
                        VALUES ({", ".join(itertools.repeat("?", len(TABLE_COLUMNS[1:])))});""",  # nosec B608 # BNS:6b6392
                (entry[1:] for entry in entries),
            )

    def get(self, query: QueryGET) -> Iterable[Sequence[object]]:
        """Retrieve entries from the history table.

        Always return all columns, since they are filtered elsewhere.
        """
        sqlite_query, sqlite_arguments = filters_to_sqlite_query(query.filters)
        if query.limit:
            sqlite_query += " LIMIT ?"
            sqlite_arguments += f" {query.limit + 1}"
        with self.conn as connection:
            cur = connection.cursor()
            cur.execute(sqlite_query, sqlite_arguments)
            return cur.fetchall()

    def housekeeping(self) -> None:
        """Remove old entries from the history table.

        And performs a vacuum to shrink the database file.
        """
        now = time.time()
        if now - self._last_housekeeping > self._config["sqlite_housekeeping_interval"]:
            delta = now - timedelta(days=self._config["history_lifetime"]).total_seconds()
            with self.conn as connection:
                cur = connection.cursor()
                cur.execute("DELETE FROM history WHERE time <= ?;", (delta,))
            # should be executed outside of the transaction
            self._vacuum()
            self._last_housekeeping = now

    def _vacuum(self) -> None:
        """Run VACUUM command only if the free pages in DB are greater than 50 Mb."""
        with self.conn as connection:
            freelist_count = connection.execute("PRAGMA freelist_count").fetchone()[0]
            freelist_size = freelist_count * self._page_size

        if freelist_size > self._config["sqlite_freelist_size"]:
            self.conn.execute("VACUUM;")

    def close(self) -> None:
        """Explicitly close the connection to the sqlite database.

        Used during a new object instantiation,
        to avoid sqlite3.OperationalError: database is locked.
        """
        self.conn.commit()
        self.conn.close()

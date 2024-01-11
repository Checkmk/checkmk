#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""EC History sqlite backend"""

from collections.abc import Iterable, Sequence
from logging import Logger

from .config import Config
from .event import Event
from .history import History, HistoryWhat
from .query import Columns, QueryGET
from .settings import Settings


class SQLiteHistory(History):
    def __init__(
        self,
        settings: Settings,
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

    def flush(self) -> None:
        """
        docstring
        """

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

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared in-memory cursor/connection stand-ins for QA-metrics tests.

``RecordingCursor`` records the rendered SQL strings via
``psycopg.sql.Composed.as_string(None)`` so identifier escaping and placeholder
counts can be asserted without a live postgres. ``fetchone`` reads from a
queue so tests can stage multi-step SELECT/INSERT-RETURNING flows.
"""

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Self

from psycopg.sql import Composed


@dataclass
class RecordingCursor:
    queries: list[str] = field(default_factory=list)
    params: list[list[object]] = field(default_factory=list)
    _fetch_queue: deque[tuple[object, ...] | None] = field(default_factory=deque)

    def queue_fetchone(self, *results: tuple[object, ...] | None) -> None:
        """Append rows to be returned by subsequent ``fetchone`` calls."""
        self._fetch_queue.extend(results)

    def execute(self, query: object, params: Iterable[object] | None = None) -> None:
        rendered = query.as_string(None) if isinstance(query, Composed) else str(query)
        self.queries.append(rendered)
        self.params.append(list(params or []))

    def fetchone(self) -> tuple[object, ...] | None:
        if not self._fetch_queue:
            return None
        return self._fetch_queue.popleft()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        return None


class FakeDb:
    """Minimal stand-in for :class:`tests.qa_metrics.db.MetabasePostgres`."""

    def __init__(self, cursor: RecordingCursor | None = None) -> None:
        self.cur = cursor if cursor is not None else RecordingCursor()

    def cursor(self) -> RecordingCursor:
        return self.cur

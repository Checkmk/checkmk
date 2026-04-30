#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from datetime import date, datetime, UTC

from tests.qa_metrics.change_quality.state import read_watermark
from tests.unit.qa_metrics._db_stubs import FakeDb, RecordingCursor


def test_read_watermark_returns_latest_commit_date() -> None:
    cursor = RecordingCursor()
    cursor.queue_fetchone((datetime(2026, 4, 28, 13, 5, 0, tzinfo=UTC),))
    db = FakeDb(cursor)

    result = read_watermark(db, "2.6.0")  # type: ignore[arg-type]

    assert result == date(2026, 4, 28)
    assert "MAX(commit_time)" in cursor.queries[0]
    assert "cmk_change_tested" in cursor.queries[0]
    assert cursor.params[0] == ["2.6.0"]


def test_read_watermark_returns_none_when_branch_has_no_rows() -> None:
    """Postgres ``MAX(commit_time)`` over zero matching rows yields ``(NULL,)``."""
    cursor = RecordingCursor()
    cursor.queue_fetchone((None,))
    db = FakeDb(cursor)
    assert read_watermark(db, "feature/x") is None  # type: ignore[arg-type]


def test_read_watermark_returns_none_when_fetchone_returns_no_row() -> None:
    """Defensive branch: postgres ``MAX(...)`` always returns a row, but the
    code guards ``result is None`` anyway -- keep the guard wired up."""
    db = FakeDb()  # empty fetch queue -> fetchone returns None
    assert read_watermark(db, "2.6.0") is None  # type: ignore[arg-type]

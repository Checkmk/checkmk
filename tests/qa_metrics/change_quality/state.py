#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""DB-backed run state for the change-quality metric.

Currently just the watermark used by incremental runs to bound the git
walk to commits not yet recorded in `cmk_change_tested`.
"""

from __future__ import annotations

from datetime import date, datetime

from tests.qa_metrics.change_quality.rows import CHANGE_TESTED
from tests.qa_metrics.db import MetabasePostgres


def read_watermark(db: MetabasePostgres, branch: str) -> date | None:
    """Latest ``commit_time`` already recorded for ``branch``, or ``None``.

    Used by incremental runs to bound the git walk. Returns a ``date`` so
    it can be passed to ``walk_werk_adds(since=)``; the walker's git
    ``--since`` argument re-includes the boundary day, and UPSERT is
    idempotent, so any double-walked rows update in place.
    """
    with db.cursor() as cursor:
        cursor.execute(
            f'SELECT MAX(commit_time) FROM "{CHANGE_TESTED.name}" WHERE branch = %s',
            (branch,),
        )
        result = cursor.fetchone()
    if result is None or result[0] is None:
        return None
    latest: datetime = result[0]
    return latest.date()

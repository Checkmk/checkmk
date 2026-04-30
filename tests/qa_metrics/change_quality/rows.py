#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Row dataclass and ``Table`` binding for ``cmk_change_tested``."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Final

from tests.qa_metrics.db import Table


@dataclass(frozen=True)
class ChangeTestedRow:
    werk_id: int
    branch: str
    werk_class: str
    werk_component: str
    werk_date: datetime
    edition: str
    level: int
    title: str
    git_commit_hash: str
    commit_time: datetime
    author_email: str | None
    subject: str | None
    gerrit_change_id: str | None
    source_component: str | None
    has_test: bool
    files_changed: int

    def to_db_dict(self) -> dict[str, Any]:
        return asdict(self)


CHANGE_TESTED: Final = Table(
    name="cmk_change_tested",
    primary_key=("werk_id", "branch"),
    row_type=ChangeTestedRow,
    schema_path=Path(__file__).with_name("schema.sql"),
)

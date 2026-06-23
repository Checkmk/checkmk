#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Row dataclasses and ``Table`` bindings for the code-coverage tables.

Both tables are declared in the shared ``schema.sql``; the two ``Table`` bindings
point at the same file, so applying either one's schema creates both.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

from tests.qa_metrics.db import Table

_SCHEMA_PATH: Final = Path(__file__).with_name("schema.sql")


@dataclass(frozen=True)
class TotalCoverageRow:
    """One row of ``cmk_code_coverage_total`` -- overall coverage for a commit."""

    commit_hash: str
    covered_lines: int
    total_lines: int
    covered_functions: int
    total_functions: int
    commit_time: datetime

    def to_db_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ModuleCoverageRow:
    """One row of ``cmk_code_coverage_per_module`` -- coverage of one module."""

    module_path: str
    covered_lines: int
    total_lines: int
    covered_functions: int
    total_functions: int
    commit_hash: str
    commit_time: datetime

    def to_db_dict(self) -> dict[str, object]:
        return asdict(self)


TOTAL: Final = Table(
    name="cmk_code_coverage_total",
    primary_key=("commit_hash",),
    row_type=TotalCoverageRow,
    schema_path=_SCHEMA_PATH,
)

PER_MODULE: Final = Table(
    name="cmk_code_coverage_per_module",
    primary_key=("module_path",),
    row_type=ModuleCoverageRow,
    schema_path=_SCHEMA_PATH,
)

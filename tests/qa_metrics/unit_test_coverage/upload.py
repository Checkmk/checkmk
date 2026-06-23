#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Store code coverage statistics from a CSV file into the coverage database.

The CSV is produced by ``summary.py`` and holds one row per source
module plus a ``TOTAL`` row. This script writes that data into two tables (see
``schema.sql``), independently selected via ``--upload-totals`` and
``--upload-per-module`` (at least one is required):

* ``cmk_code_coverage_total`` (``--upload-totals``): overall coverage history,
  one row per commit. It is never overwritten; re-running the same commit updates
  its row in place.
* ``cmk_code_coverage_per_module`` (``--upload-per-module``): per-module coverage
  of the most recent run. This table is rewritten in full so it always reflects
  the latest state of the code base.

The schema is idempotent (``CREATE TABLE/INDEX IF NOT EXISTS``) and applied
automatically on every upload, so the target tables need no separate setup step.

The database connection is read from the environment via
:meth:`tests.qa_metrics.db.MetabasePostgres.from_env` (see that module for the
recognised variables). Run as a module so the absolute imports resolve.
"""

import argparse
import csv
import logging
from collections.abc import Sequence
from dataclasses import dataclass, fields
from datetime import datetime
from pathlib import Path

from psycopg import sql

from tests.qa_metrics.db import apply_schema_file, MetabasePostgres
from tests.qa_metrics.unit_test_coverage.rows import (
    ModuleCoverageRow,
    PER_MODULE,
    TOTAL,
    TotalCoverageRow,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CoverageCounts:
    """Covered and total line/function counts for a module or the whole repo."""

    covered_lines: int
    total_lines: int
    covered_functions: int
    total_functions: int


@dataclass(frozen=True)
class ModuleCoverage:
    """Coverage counts for a single source module."""

    module_path: str
    counts: CoverageCounts


def replace_module_coverage(db: MetabasePostgres, rows: Sequence[ModuleCoverageRow]) -> None:
    """Atomically replace the per-module table with the given rows.

    ``Table.upsert`` can only insert-or-update single rows, so the full rewrite
    keeps a bespoke ``TRUNCATE`` + bulk ``INSERT`` in one transaction: concurrent
    readers keep seeing the previous run's data until the swap commits. Columns
    are derived from the row dataclass so they stay aligned with ``to_db_dict``.
    """
    columns = [field.name for field in fields(ModuleCoverageRow)]
    truncate = sql.SQL("TRUNCATE {table}").format(table=sql.Identifier(PER_MODULE.name))
    insert = sql.SQL("INSERT INTO {table} ({columns}) VALUES ({placeholders})").format(
        table=sql.Identifier(PER_MODULE.name),
        columns=sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        placeholders=sql.SQL(", ").join([sql.Placeholder()] * len(columns)),
    )
    with db.connection.transaction(), db.cursor() as cursor:
        cursor.execute(truncate)
        cursor.executemany(insert, [list(row.to_db_dict().values()) for row in rows])
    logger.info("Replaced per-module coverage with %d modules", len(rows))


def _sum_counts(modules: Sequence[ModuleCoverage]) -> CoverageCounts:
    return CoverageCounts(
        covered_lines=sum(module.counts.covered_lines for module in modules),
        total_lines=sum(module.counts.total_lines for module in modules),
        covered_functions=sum(module.counts.covered_functions for module in modules),
        total_functions=sum(module.counts.total_functions for module in modules),
    )


def read_coverage_csv(csv_file: Path) -> tuple[CoverageCounts, list[ModuleCoverage]]:
    """Read total and per-module coverage from a ``summary.py`` CSV.

    The total is taken from the ``TOTAL`` row if present, otherwise summed from
    the per-module rows.
    """
    modules: list[ModuleCoverage] = []
    total: CoverageCounts | None = None

    with csv_file.open(encoding="utf-8") as csvfile:
        for row in csv.DictReader(csvfile):
            counts = CoverageCounts(
                covered_lines=int(row["covered_lines"]),
                total_lines=int(row["total_lines"]),
                covered_functions=int(row["covered_functions"]),
                total_functions=int(row["total_functions"]),
            )
            if row["file_path"] == "TOTAL":
                total = counts
            else:
                modules.append(ModuleCoverage(module_path=row["file_path"], counts=counts))

    return total if total is not None else _sum_counts(modules), modules


class _Args(argparse.Namespace):
    csv_file: Path
    git_commit_hash: str
    commit_time: datetime
    upload_totals: bool
    upload_per_module: bool
    log_level: str


def parse_args() -> _Args:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv-file", type=Path, required=True, help="Path to the CSV coverage data file"
    )
    parser.add_argument(
        "--git-commit-hash", type=str, required=True, help="Git commit hash of the check_mk repo"
    )
    parser.add_argument(
        "--commit-time",
        type=datetime.fromisoformat,
        required=True,
        help="Git committer time in ISO format, e.g. 2025-10-16T12:05:43+02:00",
    )
    parser.add_argument(
        "--upload-totals",
        action="store_true",
        help="Store the overall coverage in the history table",
    )
    parser.add_argument(
        "--upload-per-module",
        action="store_true",
        help="Rewrite the per-module coverage table from the CSV",
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO", help="Logging level (default: %(default)s)"
    )

    args = parser.parse_args(namespace=_Args())
    if not (args.upload_totals or args.upload_per_module):
        parser.error("at least one of --upload-totals / --upload-per-module is required")
    return args


def main() -> None:
    logging.basicConfig()
    args = parse_args()
    logger.setLevel(args.log_level)

    if not args.csv_file.is_file():
        raise FileNotFoundError(f"CSV file not found: {args.csv_file}")

    total, modules = read_coverage_csv(args.csv_file)
    logger.info("Read coverage for %d modules from %s", len(modules), args.csv_file)

    with MetabasePostgres.from_env() as db:
        apply_schema_file(db, TOTAL.schema_path)
        if args.upload_totals:
            TOTAL.upsert(
                db,
                TotalCoverageRow(
                    commit_hash=args.git_commit_hash,
                    covered_lines=total.covered_lines,
                    total_lines=total.total_lines,
                    covered_functions=total.covered_functions,
                    total_functions=total.total_functions,
                    commit_time=args.commit_time,
                ),
            )
            logger.info("Stored total coverage for commit %s", args.git_commit_hash)
        if args.upload_per_module:
            replace_module_coverage(
                db,
                [
                    ModuleCoverageRow(
                        module_path=module.module_path,
                        covered_lines=module.counts.covered_lines,
                        total_lines=module.counts.total_lines,
                        covered_functions=module.counts.covered_functions,
                        total_functions=module.counts.total_functions,
                        commit_hash=args.git_commit_hash,
                        commit_time=args.commit_time,
                    )
                    for module in modules
                ],
            )

    logger.info("Code coverage storage completed successfully")


if __name__ == "__main__":
    main()

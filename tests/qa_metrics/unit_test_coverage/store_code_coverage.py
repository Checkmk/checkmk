#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Store code coverage statistics from a CSV file into the coverage database.

The CSV is produced by ``code_coverage_summary.py`` and holds one row per source
module plus a ``TOTAL`` row. This script writes that data into two tables (see
``code_coverage_tables.sql``), independently selected via ``--upload-totals`` and
``--upload-per-module`` (at least one is required):

* ``cmk_code_coverage_total`` (``--upload-totals``): overall coverage history,
  one row per commit. It is never overwritten; re-running the same commit updates
  its row in place.
* ``cmk_code_coverage_per_module`` (``--upload-per-module``): per-module coverage
  of the most recent run. This table is rewritten in full so it always reflects
  the latest state of the code base.

The schema is idempotent (``CREATE TABLE/INDEX IF NOT EXISTS``) and applied
automatically on every upload, so the target tables need no separate setup step.

Connection parameters default to environment variables (see ``--help``). The
database password is read from QA_POSTGRES_PASSWORD; if it is unset, SSL client
certificates must be provided instead.
"""

import argparse
import csv
import logging
import os
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import get_args, Literal

import psycopg
from psycopg import sql

logger = logging.getLogger(__name__)

type SslMode = Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]

_TABLE_TOTAL = "cmk_code_coverage_total"
_TABLE_PER_MODULE = "cmk_code_coverage_per_module"

_SCHEMA_FILE = Path(__file__).with_name("code_coverage_tables.sql")


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


class CodeCoverageDb:
    """Connection wrapper for storing coverage data in PostgreSQL."""

    def __init__(
        self,
        host: str,
        port: int,
        dbname: str,
        user: str,
        sslrootcert: Path | None = None,
        sslcert: Path | None = None,
        sslkey: Path | None = None,
        sslmode: SslMode = "allow",
    ) -> None:
        if password := os.getenv("QA_POSTGRES_PASSWORD"):
            dsn = f"dbname={dbname} user={user} host={host} port={port} password={password}"
        elif sslcert and sslkey and sslrootcert:
            dsn = (
                f"sslmode={sslmode} dbname={dbname} user={user} host={host} port={port} "
                f"sslrootcert={sslrootcert} sslcert={sslcert} sslkey={sslkey}"
            )
        else:
            raise ValueError("Database password or SSL certificates must be provided")

        self._connection = psycopg.connect(dsn, autocommit=True)
        logger.info("Connected to database %s@%s:%s", dbname, host, port)

    def __enter__(self) -> "CodeCoverageDb":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        if not self._connection.closed:
            self._connection.close()
            logger.debug("Database connection closed")

    def apply_schema(self, schema_file: Path) -> None:
        """Apply the idempotent table DDL so the target tables exist.

        The schema carries its own BEGIN/COMMIT and has no query parameters, so
        the autocommit connection runs all statements via the simple-query
        protocol in a single call.
        """
        self._connection.execute(schema_file.read_text(encoding="utf-8"))
        logger.info("Applied schema from %s", schema_file)

    def store_total_coverage(
        self, counts: CoverageCounts, commit_hash: str, commit_time: datetime
    ) -> None:
        """Append the overall coverage for a commit, updating it if it exists."""
        query = sql.SQL(
            """
            INSERT INTO {table}
                (commit_hash, covered_lines, total_lines, covered_functions,
                 total_functions, commit_time)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (commit_hash) DO UPDATE SET
                covered_lines = EXCLUDED.covered_lines,
                total_lines = EXCLUDED.total_lines,
                covered_functions = EXCLUDED.covered_functions,
                total_functions = EXCLUDED.total_functions,
                commit_time = EXCLUDED.commit_time
            """
        ).format(table=sql.Identifier(_TABLE_TOTAL))
        with self._connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    commit_hash,
                    counts.covered_lines,
                    counts.total_lines,
                    counts.covered_functions,
                    counts.total_functions,
                    commit_time,
                ),
            )
        logger.info("Stored total coverage for commit %s", commit_hash)

    def replace_module_coverage(
        self, modules: Sequence[ModuleCoverage], commit_hash: str, commit_time: datetime
    ) -> None:
        """Atomically replace the per-module table with the given modules.

        The truncate and inserts run in a single transaction, so concurrent
        readers keep seeing the previous run's data until the swap commits.
        """
        truncate = sql.SQL("TRUNCATE {table}").format(table=sql.Identifier(_TABLE_PER_MODULE))
        insert = sql.SQL(
            """
            INSERT INTO {table}
                (module_path, covered_lines, total_lines, covered_functions,
                 total_functions, commit_hash, commit_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
        ).format(table=sql.Identifier(_TABLE_PER_MODULE))
        rows = [
            (
                module.module_path,
                module.counts.covered_lines,
                module.counts.total_lines,
                module.counts.covered_functions,
                module.counts.total_functions,
                commit_hash,
                commit_time,
            )
            for module in modules
        ]
        with self._connection.transaction(), self._connection.cursor() as cursor:
            cursor.execute(truncate)
            cursor.executemany(insert, rows)
        logger.info("Replaced per-module coverage with %d modules", len(rows))


def _sum_counts(modules: Sequence[ModuleCoverage]) -> CoverageCounts:
    return CoverageCounts(
        covered_lines=sum(module.counts.covered_lines for module in modules),
        total_lines=sum(module.counts.total_lines for module in modules),
        covered_functions=sum(module.counts.covered_functions for module in modules),
        total_functions=sum(module.counts.total_functions for module in modules),
    )


def read_coverage_csv(csv_file: Path) -> tuple[CoverageCounts, list[ModuleCoverage]]:
    """Read total and per-module coverage from a ``code_coverage_summary.py`` CSV.

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
    dbname: str
    dbuser: str
    dbhost: str
    dbport: int
    sslmode: SslMode
    sslrootcert: Path | None
    sslcert: Path | None
    sslkey: Path | None
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
        "--dbhost", type=str, default=os.getenv("POSTGRES_HOST"), help="Database host"
    )
    parser.add_argument(
        "--dbport", type=int, default=int(os.getenv("POSTGRES_PORT", "5432")), help="Database port"
    )
    parser.add_argument(
        "--dbname", type=str, default=os.getenv("POSTGRES_DB"), help="Database name"
    )
    parser.add_argument(
        "--dbuser", type=str, default=os.getenv("QA_POSTGRES_USER"), help="Database user"
    )
    parser.add_argument(
        "--sslmode",
        choices=get_args(SslMode.__value__),
        default="allow",
        help="SSL mode for the database connection (default: %(default)s)",
    )
    parser.add_argument(
        "--sslrootcert",
        type=Path,
        default=os.getenv("QA_ROOT_CERT"),
        help="Path to the SSL root certificate (default from env QA_ROOT_CERT)",
    )
    parser.add_argument(
        "--sslcert",
        type=Path,
        default=os.getenv("QA_POSTGRES_CERT"),
        help="Path to the SSL client certificate (default from env QA_POSTGRES_CERT)",
    )
    parser.add_argument(
        "--sslkey",
        type=Path,
        default=os.getenv("QA_POSTGRES_KEY"),
        help="Path to the SSL client key (default from env QA_POSTGRES_KEY)",
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO", help="Logging level (default: %(default)s)"
    )

    args = parser.parse_args(namespace=_Args())
    if not (args.upload_totals or args.upload_per_module):
        parser.error("at least one of --upload-totals / --upload-per-module is required")
    return args


def _validate_ssl_files(sslrootcert: Path, sslcert: Path, sslkey: Path) -> None:
    for name, path in (
        ("root cert", sslrootcert),
        ("client cert", sslcert),
        ("client key", sslkey),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"SSL {name} file not found: {path}")


def main() -> None:
    logging.basicConfig()
    args = parse_args()
    logger.setLevel(args.log_level)

    if not args.csv_file.is_file():
        raise FileNotFoundError(f"CSV file not found: {args.csv_file}")
    if args.sslrootcert and args.sslcert and args.sslkey:
        _validate_ssl_files(args.sslrootcert, args.sslcert, args.sslkey)

    total, modules = read_coverage_csv(args.csv_file)
    logger.info("Read coverage for %d modules from %s", len(modules), args.csv_file)

    with CodeCoverageDb(
        host=args.dbhost,
        port=args.dbport,
        dbname=args.dbname,
        user=args.dbuser,
        sslrootcert=args.sslrootcert,
        sslcert=args.sslcert,
        sslkey=args.sslkey,
        sslmode=args.sslmode,
    ) as db:
        db.apply_schema(_SCHEMA_FILE)
        if args.upload_totals:
            db.store_total_coverage(total, args.git_commit_hash, args.commit_time)
        if args.upload_per_module:
            db.replace_module_coverage(modules, args.git_commit_hash, args.commit_time)

    logger.info("Code coverage storage completed successfully")


if __name__ == "__main__":
    main()

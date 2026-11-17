#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The command line of perftest_plot.py."""

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

import argparse
import re
from collections.abc import Callable
from pathlib import Path
from typing import get_args

from tests.performance.reporting.performance_db import SslMode


class PerftestPlotArgs(argparse.Namespace):
    """
    Arguments for configuring performance test plotting.

    Attributes:
        root_dir (Path): The root directory containing performance test data.
        output_dir (Path | None): Directory to store generated plots and outputs.
            If None, the path for the highest version job is used.
        skip_filesystem_reads (bool): If True, skip reading data from the filesystem.
        skip_filesystem_writes (bool): If True, skip writing data to the filesystem.
        skip_database_reads (bool): If True, skip reading data from the database.
        skip_database_writes (bool): If True, skip writing data to the database.
        skip_graph_generation (bool): If True, skip generating graphs.
        write_json_files (bool): If True, write output data to JSON files.
        job_names (list[str]): List of job names to include in the performance test.
        dbname (str): Name of the database to connect to.
        dbuser (str): Username for database authentication.
        dbhost (str): Hostname or IP address of the database server.
        dbport (int): Port number for the database connection.
        dbcheck (bool): If True, DB connection is checked only (nothing else is done).
        require_database (bool): Fail instead of falling back to the filesystem when the
            database can not be reached.
        validate_baselines (bool): Enable performance baseline validation.
        alert_on_failure (bool): Enable Jira alerter on baseline validation failure.
        warn_only (bool): Report a failed baseline validation without exiting non-zero.
        sslmode (SslMode): The SSL mode for the Postgres authentication.
        sslrootcert (Path): The path of the root certificate.
        sslcert (Path): The path of the Postgres certificate.
        sslkey (Path): The path of the Postgres key.
        jira_url (str): The URL of the Jira server.
        jira_token_var (str): The name of the environment variable that holds the Jira token.
        jira_token_path (Path): The path of file that holds the Jira token.
        branch_version (str): The default branch version.
        edition (str): The default edition.
        update_db (bool): If True, update existing job data in the database.
        purge_db (bool): If True, delete existing job data from the database.
        append_db (bool): If True, replace only the uploaded scenarios of existing jobs.
        product_release (str): The product release of the stored jobs.
        baseline_offset (int): The offset for the baseline validation.
        cpu_tolerance (float): The tolerance level for the CPU baseline validation.
        mem_tolerance (float): The tolerance level for the memory baseline validation.
        runtime_tolerance (float): The tolerance level for the runtime baseline validation.
        log_level (str): Logging level of the application.
    """

    root_dir: Path
    output_dir: Path | None
    skip_filesystem_reads: bool
    skip_filesystem_writes: bool
    skip_database_reads: bool
    skip_database_writes: bool
    skip_graph_generation: bool
    write_json_files: bool
    job_names: list[str]
    dbname: str
    dbuser: str
    dbhost: str
    dbport: int
    dbcheck: bool
    require_database: bool
    validate_baselines: bool
    alert_on_failure: bool
    warn_only: bool
    sslmode: SslMode
    sslrootcert: Path
    sslcert: Path
    sslkey: Path
    jira_url: str
    jira_token_var: str
    jira_token_path: Path
    branch_version: str
    edition: str
    update_db: bool
    purge_db: bool
    append_db: bool
    product_release: str
    baseline_offset: int
    cpu_tolerance: float
    mem_tolerance: float
    runtime_tolerance: float
    log_level: str


def parse_args() -> PerftestPlotArgs:
    """
    Parse command line arguments for the performance test plotting tool.

    Returns:
        PerftestPlotArgs: An object containing parsed command line arguments.

    Raises:
        argparse.ArgumentTypeError: If a job name does not match the required pattern.
    """

    repo_root_dir = Path(__file__).parent.parent.parent.parent

    def job_name() -> Callable:
        pattern = r"[0-9](\.[0-9]){2}-[0-9]{4}(\.[0-9]{2}){2}\.[a-z]*(_[0-9]+)?"

        def validator(value: str) -> str:
            if not (match := re.search(pattern, value)):
                raise argparse.ArgumentTypeError(
                    f"Value '{value}' does not match pattern: {pattern}"
                )
            return match.group(0)

        return validator

    def sslmode() -> Callable:
        def validator(value: str) -> str:
            if value in get_args(SslMode):
                return value
            raise argparse.ArgumentTypeError(f"Value '{value}' is not a valid sslmode!")

        return validator

    parser = argparse.ArgumentParser(
        description="Plots graphs for the given performance test jobs."
    )
    parser.add_argument(
        dest="job_names",
        type=job_name(),
        default=[],
        nargs="*",
        help="Job names to process (in the format <VERSION>-<DATE>-<EDITION>).",
    )
    parser.add_argument(
        "--root-dir",
        "-r",
        dest="root_dir",
        type=Path,
        default=repo_root_dir / "results" / "performance",
        help="The root directory for all job files on disk (default: %(default)s).",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        dest="output_dir",
        type=Path,
        default=None,
        help="The output path for the graph files. Defaults to the highest version.",
    )
    parser.add_argument(
        "--skip-filesystem-reads",
        action=argparse.BooleanOptionalAction,
        dest="skip_filesystem_reads",
        default=False,
        help="Specifies to read from the database only and ignore filesystem data"
        " (default: %(default)s).",
    )
    parser.add_argument(
        "--skip-filesystem-writes",
        action=argparse.BooleanOptionalAction,
        dest="skip_filesystem_writes",
        default=False,
        help="Specifies to update the database only and skip writing to the filesystem"
        " (default: %(default)s).",
    )
    parser.add_argument(
        "--skip-database-reads",
        action=argparse.BooleanOptionalAction,
        dest="skip_database_reads",
        default=False,
        help="Specifies to read from the filesystem only and ignore database data"
        " (default: %(default)s).",
    )
    parser.add_argument(
        "--skip-database-writes",
        action=argparse.BooleanOptionalAction,
        dest="skip_database_writes",
        default=False,
        help="Specifies to update the filesystem only and skip writing to the database"
        " (default: %(default)s).",
    )
    parser.add_argument(
        "--skip-graph-generation",
        action=argparse.BooleanOptionalAction,
        dest="skip_graph_generation",
        default=False,
        help="Specifies to skip the graph generation (default: %(default)s).",
    )
    parser.add_argument(
        "--write-json-files",
        action=argparse.BooleanOptionalAction,
        dest="write_json_files",
        default=False,
        help="Specifies to write JSON files back to the filesystem (default: %(default)s).",
    )
    parser.add_argument(
        "--dbname",
        dest="dbname",
        type=str,
        default="performance",
        help="The database name to connect to (default: %(default)s).",
    )
    parser.add_argument(
        "--dbuser",
        dest="dbuser",
        type=str,
        default="performance",
        help="The user name for the database connection (default: %(default)s).",
    )
    parser.add_argument(
        "--dbhost",
        dest="dbhost",
        type=str,
        default=None,
        help="The host name for the database connection (default: %(default)s).",
    )
    parser.add_argument(
        "--dbport",
        dest="dbport",
        type=int,
        default=5432,
        help="The port for the database connection (default: %(default)d).",
    )
    parser.add_argument(
        "--dbcheck",
        action=argparse.BooleanOptionalAction,
        dest="dbcheck",
        default=False,
        help="Specifies if the DB connection should be checked only (default: %(default)s).",
    )
    parser.add_argument(
        "--require-database",
        action=argparse.BooleanOptionalAction,
        dest="require_database",
        default=False,
        help="Specifies to fail instead of falling back to the filesystem when the database"
        " can not be reached (default: %(default)s).",
    )
    parser.add_argument(
        "--validate-baselines",
        action=argparse.BooleanOptionalAction,
        dest="validate_baselines",
        default=False,
        help="Enable performance baseline validation (default: %(default)s).",
    )
    parser.add_argument(
        "--alert-on-failure",
        action=argparse.BooleanOptionalAction,
        dest="alert_on_failure",
        default=False,
        help="Enable Jira alerter on baseline validation failure (default: %(default)s).",
    )
    parser.add_argument(
        "--warn-only",
        action=argparse.BooleanOptionalAction,
        dest="warn_only",
        default=False,
        help="Report a failed baseline validation without exiting non-zero (default: %(default)s).",
    )
    parser.add_argument(
        "--sslrootcert",
        dest="sslrootcert",
        type=Path,
        default=(
            user_sslrootcert
            if (user_sslrootcert := Path().home() / ".postgresql/root.crt").exists()
            else repo_root_dir / "QA_ROOT_CERT"
        ),
        help="The name of the root certificate variable (default: %(default)s).",
    )
    parser.add_argument(
        "--sslcert",
        dest="sslcert",
        type=Path,
        default=(
            user_sslcert
            if (user_sslcert := Path().home() / ".postgresql/postgresql.crt").exists()
            else repo_root_dir / "QA_POSTGRES_CERT"
        ),
        help="The name of the Postgres certificate variable (default: %(default)s).",
    )
    parser.add_argument(
        "--sslkey",
        dest="sslkey",
        type=Path,
        default=(
            user_sslkey
            if (user_sslkey := Path().home() / ".postgresql/postgresql.key").exists()
            else repo_root_dir / "QA_POSTGRES_KEY"
        ),
        help="The name of the Postgres key variable (default: %(default)s).",
    )
    parser.add_argument(
        "--sslmode",
        dest="sslmode",
        type=sslmode(),
        default="require",
        help="The SSL mode for the Postgres authentication (default: %(default)s).",
    )
    parser.add_argument(
        "--jira-url",
        dest="jira_url",
        type=str,
        default=None,
        help="The URL of the Jira server (default: %(default)s).",
    )
    parser.add_argument(
        "--jira-token-var",
        dest="jira_token_var",
        type=str,
        default="QA_JIRA_API_TOKEN",
        help="The name of the Jira token variable (default: %(default)s).",
    )
    parser.add_argument(
        "--jira-token-path",
        dest="jira_token_path",
        type=Path,
        default=None,
        help="The path to the Jira token file (default: %(default)s).",
    )
    parser.add_argument(
        "--branch-version",
        dest="branch_version",
        type=str,
        default="2.4.0",
        help="The default branch version for jobs (default: %(default)s).",
    )
    parser.add_argument(
        "--edition",
        dest="edition",
        type=str,
        default="cee",
        help="The default edition for jobs (default: %(default)s).",
    )
    db_writes = parser.add_mutually_exclusive_group()
    db_writes.add_argument(
        "--update-db",
        action=argparse.BooleanOptionalAction,
        dest="update_db",
        default=False,
        help="Specifies if the DB will be updated, even if job data for that job exists already.",
    )
    db_writes.add_argument(
        "--purge-db",
        action=argparse.BooleanOptionalAction,
        dest="purge_db",
        default=False,
        help="Specifies if the DB will be purged, if job data for a selected job exists already.",
    )
    db_writes.add_argument(
        "--append-db",
        action=argparse.BooleanOptionalAction,
        dest="append_db",
        default=False,
        help=(
            "Specifies if the scenarios will be added to existing jobs, replacing only the stored"
            " results of the same scenarios."
        ),
    )
    parser.add_argument(
        "--product-release",
        dest="product_release",
        type=str,
        default="",
        help="The product release of the stored jobs, e.g. 2.4.0-2026.11.16 (default: none).",
    )
    parser.add_argument(
        "--baseline-offset",
        dest="baseline_offset",
        type=int,
        default=0,
        help=(
            "Specifies the number of days in the past to use for the baseline validation"
            "(default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--cpu-tolerance",
        dest="cpu_tolerance",
        type=float,
        default=15.0,
        help=(
            "Specifies the tolerance percentage to which the CPU baseline may be exceeded"
            " (default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--mem-tolerance",
        dest="mem_tolerance",
        type=float,
        default=10.0,
        help=(
            "Specifies the tolerance percentage to which the memory baseline may be exceeded"
            "(default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--runtime-tolerance",
        dest="runtime_tolerance",
        type=float,
        default=10.0,
        help=(
            "Specifies the tolerance percentage to which the runtime baseline may be exceeded"
            " (default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        type=str,
        default="WARNING",
        help="The log level for the application (default: %(default)s).",
    )
    return parser.parse_args(namespace=PerftestPlotArgs())

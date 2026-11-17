#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""
Plot performance data from filesystem or database.

This script provides a CLI tool for aggregating, storing, and visualizing performance test results
from either a PostgreSQL database or the local filesystem.

It supports reading and writing benchmark and resource usage data, generating graphs for execution
times and resource consumption, and exporting results to JSON files.

Main Features:
- Read performance test jobs and scenarios from disk or database.
- Write performance data to disk (JSON) and/or database.
- Generate benchmark and resource usage graphs using matplotlib.
- Flexible configuration via command-line arguments for input/output sources, database credentials,
  and job selection.

Usage:
    python3 -m tests.performance.reporting.perftest_plot [options] <job_names>

Options:
    --root-dir, -r           Root directory for job files (default: results/performance).
    --output-dir, -o         Output directory for graph files.
    --skip-filesystem-reads  Read only from database.
    --skip-filesystem-writes Write only to database.
    --skip-database-reads    Read only from filesystem.
    --skip-database-writes   Write only to filesystem.
    --skip-graph-generation  Skip graph generation.
    --write-json-files       Write JSON files to filesystem.
    --dbname                 Database name (default: performance).
    --dbuser                 Database user (default: performance).
    --dbhost                 Database host (default: None).
    --dbport                 Database port (default: 5432).
    --require-database       Fail if the database can not be reached.
    --append-db              Replace only the uploaded scenarios of existing jobs.
    --product-release        The product release of the stored jobs.
    --validate-baselines     Whether to perform baseline validation.
    --alert-on-failure       Whether to alert on failed baseline validation.
    --warn-only              Report failed baseline validation without a non-zero exit code.
    --log-level              Set the log level for the application.
    --branch-version         Set the default branch-version.
    --edition                Set the default edition.
    job_names                List of job names to process.

Without --update-db or --append-db, a run of a job that is stored already with other results is
stored as a further job, named after the job with the suffix "_2", "_3" and so on.

Example:
    python3 -m tests.performance.reporting.perftest_plot --dbhost qa.lan.checkmk.net \
        2.4.0-2025.09.10.cee
"""

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

import json
import logging
import re
from collections.abc import Sequence
from datetime import date, timedelta
from datetime import datetime as Datetime
from os import getenv
from pathlib import Path
from statistics import fmean
from sys import exit as sys_exit
from typing import NamedTuple

import psycopg
from jira import JIRA

from tests.performance.reporting.performance_args import parse_args, PerftestPlotArgs
from tests.performance.reporting.performance_db import (
    Measurements,
    MeasurementsList,
    PerformanceData,
    PerformanceDb,
)
from tests.performance.reporting.performance_graphs import PerformanceGraphs

logging.basicConfig()
logger = logging.getLogger(__name__)


class AverageValues(NamedTuple):
    avg_time: float
    avg_cpu: float
    avg_mem: float


class SkippedScenario(NamedTuple):
    """Represents a scenario that should be skipped during validation.

    Attributes:
        pattern: A regex pattern to match the scenario name against.
        reason: Human-readable explanation for why the scenario is skipped.
        condition: Optional boolean indicating if the scenario should be skipped.
    """

    pattern: str
    reason: str
    condition: bool = True


class BaselineAlert(NamedTuple):
    """Represents a finding of the baseline validation.

    Attributes:
        message: Human-readable description of the finding.
        is_failure: Whether the finding should fail the job. Findings that merely report
            the absence of data are reported, but do not fail the job.
    """

    message: str
    is_failure: bool = True


class PerftestPlot:
    def __init__(self, args: PerftestPlotArgs):
        """
        Initializes the performance test plot object with the provided arguments.

        Args:
            args (PerftestPlotArgs): Configuration arguments for performance test plotting.

        Raises:
            psycopg.OperationalError: If unable to connect to the database.
        """
        super().__init__()
        self.args = args

        self.cpu_usage_metric = "cpu_info.cpu_percent"
        self.memory_usage_metric = "memory_info.virtual_memory_percent"

        self.root_dir = self.args.root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.update_db = self.args.update_db and len(self.args.job_names) > 0
        self.purge_db = self.args.purge_db and len(self.args.job_names) > 0
        self.append_db = self.args.append_db
        self.read_from_database = not (
            self.args.skip_database_reads or self.update_db or self.purge_db
        )
        self.read_from_filesystem = not self.args.skip_filesystem_reads
        self.write_to_database = not self.args.skip_database_writes

        if self.args.dbhost and (self.read_from_database or self.write_to_database):
            try:
                self.database = PerformanceDb(
                    sslrootcert=self.args.sslrootcert,
                    sslcert=self.args.sslcert,
                    sslkey=self.args.sslkey,
                    sslmode=self.args.sslmode,
                    dbname=self.args.dbname,
                    user=self.args.dbuser,
                    host=self.args.dbhost,
                    port=self.args.dbport,
                )
                print("A connection was successfully established with the database!")
            except psycopg.OperationalError as excp:
                if self.args.require_database:
                    sys_exit(f'Could not connect to database "{self.args.dbname}"!\n\n{excp}')
                print(
                    f'Could not connect to database "{self.args.dbname}"; '
                    f"switching to filesystem mode!\n\n{excp}",
                )
                self.read_from_database = self.write_to_database = False
        else:
            print("Database access disabled; switching to filesystem mode!")
            self.read_from_database = self.write_to_database = False

        if self.args.dbcheck:
            self.jobs = {}
            sys_exit()

        self.write_json_files = self.args.write_json_files and not (
            self.args.skip_filesystem_writes or self.update_db or self.purge_db
        )
        self.write_graph_files = not (
            self.args.skip_graph_generation
            or self.args.skip_filesystem_writes
            or self.update_db
            or self.purge_db
        )
        self.jira_url = self.args.jira_url
        self.jira_token = self._read_jira_token()
        self.alert_on_failure = self.args.alert_on_failure and self.jira_url and self.jira_token
        self.validate_baselines = (
            self.args.validate_baselines or self.alert_on_failure
        ) and not self.purge_db
        self.warn_only = self.args.warn_only
        self.job_names = self._read_job_names()
        self.scenario_names = self._read_scenario_names()
        self.jobs = self.read_performance_data()
        self.output_dir = self.args.output_dir or (
            self._job_file_path(self.job_names[-1]).parent if self.job_names else self.root_dir
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _read_json(json_path: Path) -> Measurements | MeasurementsList | None:
        """
        Reads and parses a JSON file from the given path.

        Args:
            json_path (Path): The path to the JSON file.

        Returns:
            Measurements | MeasurementsList | None: The parsed JSON data as a Measurements or
                MeasurementsList object, or None if the file is not found or cannot be accessed.

        Raises:
            Exception: If the JSON file cannot be decoded or another OS error occurs.
        """
        try:
            with open(json_path, encoding="utf-8") as statistics_file:
                return json.load(statistics_file)
        except (FileNotFoundError, PermissionError):
            logger.exception('File "%s" not found!', json_path)
        except (json.JSONDecodeError, OSError):
            logger.exception('Can not parse JSON file "%s"!', json_path)
        return None

    def _job_file_path(self, job_name: str) -> Path:
        """
        Returns the file path to the benchmark JSON file for a given job.

        Args:
            job_name (str): The name of the job.

        Returns:
            Path: The path to the benchmark.json file.
        """
        return self.root_dir / f"{job_name}/benchmark.json"

    def _read_jira_token(self) -> str | None:
        """
        Read JIRA authentication token from environment variable or file.

        Attempts to retrieve the JIRA token first from an environment variable
        specified by self.args.jira_token_var, and if not found, reads it from
        a file specified by self.args.jira_token_path (taking the first line).

        Returns:
            str | None: The JIRA token string if successfully retrieved,
                       None if the token cannot be read due to OSError or TypeError.
        """
        try:
            jira_token: str | None = (
                getenv(self.args.jira_token_var)
                or Path(self.args.jira_token_path).read_text().split("\n")[0]
            )
        except (OSError, TypeError):
            jira_token = None
        return jira_token

    def scenario_file_path(self, job_name: str, scenario_name: str) -> Path:
        """
        Constructs the file path for a scenario's resources JSON file.

        Args:
            job_name (str): The name of the job.
            scenario_name (str): The name of the scenario.

        Returns:
            Path: The path to the scenario's resources JSON file.
        """
        return self.root_dir / f"{job_name}/{scenario_name}.resources.json"

    def _read_job_names(self) -> list[str]:
        """
        Retrieves and returns a sorted list of job names that are either present on disk or exist
        in the database.

        The method checks for job directories in the specified root directory and verifies the
        existence of corresponding job files. It also checks the database for job names.
        Only job names that are found on disk or in the database are returned.

        Returns:
            list[str]: A sorted list of valid job names found on disk or in the database.
        """

        def baseline_jobs(offset: int = 0) -> Sequence[str]:
            num_old_jobs = 4
            return [
                (Datetime.today() - timedelta(days=offset + i)).strftime(
                    f"{self.args.branch_version}-%Y.%m.%d.{self.args.edition}"
                )
                for i in range(num_old_jobs, 0, -1)
            ] + [
                Datetime.today().strftime(
                    f"{self.args.branch_version}-%Y.%m.%d.{self.args.edition}"
                )
            ]

        job_names = (
            sorted(set(self.args.job_names))
            if self.args.job_names
            else baseline_jobs(self.args.baseline_offset)
        )

        if self.root_dir.is_dir():
            print(f'Scanning root dir "{self.root_dir}" for reports...')
            job_names_on_disk = [
                job.name
                for job in self.root_dir.iterdir()
                if job.is_dir() and self._job_file_path(job.name).exists()
            ]
        else:
            print(f'Skipping root dir "{self.root_dir}": Folder not found!')
            job_names_on_disk = []
        return sorted(
            [
                job_name
                for job_name in job_names
                if job_name in job_names_on_disk
                or (self.read_from_database and self.database.check_job(job_name))
            ]
        )

    def _read_benchmark_data(self, job_name: str) -> Measurements:
        """
        Reads benchmark job data from disk or database.

        If the job data exists on the filesystem and reading from the filesystem is enabled,
        loads and returns the data from a JSON file. Otherwise, attempts to read the job data
        from the database if enabled and the job exists in the database.

        For each scenario associated with the job, retrieves benchmark statistics and
        constructs a list of benchmark dictionaries containing scenario name, description,
        and statistics.

        Returns:
            dict: A dictionary containing benchmark data, job datetime, and machine information.
                  If no data is found, returns a dictionary with an empty 'benchmarks' list.

        Raises:
            ValueError: If the benchmark data loaded from the filesystem is not a dictionary.

        Args:
            job_name (str): The name of the job to read data for.
        """
        job_file_path = self._job_file_path(job_name)
        if job_file_path.exists() and self.read_from_filesystem:
            logger.info('Reading data for job "%s" from the filesystem...', job_name)
            data = self._read_json(job_file_path)
            if isinstance(data, dict):
                return data

        benchmarks: list[dict[str, str | Measurements]] = []
        if not (self.read_from_database and self.database.check_job(job_name)):
            return {"benchmarks": benchmarks}
        logger.info('Reading data for job "%s" from the database...', job_name)
        job_details = self.database.get_job(job_name=job_name)
        for scenario_name in self.scenario_names:
            scenario_details = self.database.get_scenario(scenario_name)
            if not scenario_details:
                continue
            scenario_id, _, scenario_description = scenario_details
            test_details = self.database.get_test(job_details.job_id, scenario_id)
            if not test_details:
                continue
            test_id = test_details[0]
            if benchmark_statistics := self.database.read_benchmark_data(test_id):
                benchmarks.append(
                    {
                        "name": scenario_name,
                        "description": scenario_description,
                        "stats": benchmark_statistics,
                    }
                )
        return {
            "benchmarks": benchmarks,
            "datetime": str(job_details.end_timestamp),
            "machine_info": {
                "node": job_details.host_name,
                "system": job_details.system_name,
                "release": job_details.system_release,
                "machine": job_details.system_machine,
            },
        }

    def _scenario_on_disk(self, job_name: str, scenario_name: str) -> bool:
        """Return whether the scenario data of a job is read from the filesystem."""
        return (
            self.read_from_filesystem and self.scenario_file_path(job_name, scenario_name).exists()
        )

    def _read_scenario_data(self, job_name: str) -> dict[str, MeasurementsList]:
        """
        Reads measurement data for each scenario associated with a given job name from either the
        filesystem or a database.

        Args:
            job_name (str): The name of the job for which scenario data should be retrieved.

        Returns:
            dict[str, MeasurementsList]: A dictionary mapping scenario names to measurement lists.

        Notes:
            - If `read_from_filesystem` and the scenario file exists, filesystem data is read.
            - If `read_from_database` and the job exists in the database, database data is read.
            - If no data is found for a scenario, an empty list is returned for that scenario.
        """
        scenario_data: dict[str, MeasurementsList] = {}
        for scenario_name in self.scenario_names:
            scenario_file_path = self.scenario_file_path(job_name, scenario_name)
            if self._scenario_on_disk(job_name, scenario_name):
                # read measurements from file
                scenario_data[scenario_name] = (
                    data if isinstance(data := self._read_json(scenario_file_path), list) else []
                )
            elif self.read_from_database and self.database.check_job(job_name=job_name):
                scenario_data[scenario_name] = self.database.read_scenario_data(
                    job_name=job_name, scenario_name=scenario_name
                )

        return scenario_data

    def _read_scenario_names(self) -> list[str]:
        """
        Retrieves a sorted list of scenario names from the filesystem and/or database.

        Scenarios are identified by files matching the pattern '*.resources.json' in the job
        directories. The scenario name is derived from the file stem, with the '.resources' suffix
        removed. If enabled, scenario names are also retrieved from the database and combined with
        those from the filesystem.

        Returns:
            list[str]: A sorted list of scenario names.
        """
        scenario_names = (
            list(
                {
                    _.stem.removesuffix(".resources")
                    for job_name in self.job_names
                    if (job_file_path := self._job_file_path(job_name)).exists()
                    for _ in list(job_file_path.parent.glob("*.resources.json"))
                }
            )
            if self.read_from_filesystem
            else []
        )
        if self.read_from_database:
            scenario_names += self.database.get_scenario_names()
        scenario_names.sort()
        return scenario_names

    def read_performance_data(self) -> PerformanceData:
        """
        Retrieve and aggregate performance data for all selected jobs.

        For each selected job, this method collects job-specific data and scenario-specific data.
        The results are returned as a sorted dictionary mapping each job name to a tuple containing
        its job data and scenario data.

        Returns:
            PerformanceData: A sorted dictionary where each key is a job name and each value is a
            tuple of (job_data, scenario_data) for that job.
        """
        return dict(
            sorted(
                {
                    job_name: (
                        self._read_benchmark_data(job_name),
                        self._read_scenario_data(job_name),
                    )
                    for job_name in self.job_names
                }.items()
            )
        )

    def write_performance_data(self) -> None:
        """
        Writes performance data for each job and scenario to JSON files and/or a database.

        For each selected job, this method:
        - Writes the job benchmark data to a JSON file if `write_json_files` is True.
        - Iterates through each scenario in the job, optionally writing scenario performance data
        to a JSON file.
        - If performance data exists for a scenario, and `write_to_database` is True, writes the
        data to the database, including job and test start/end times.

        Notes:
            - Test start and end times are extracted from the first and last entries in the
            scenario performance data.

        Raises:
            Any exceptions raised during file or database operations are propagated.
        """
        for job_name in self.jobs:
            benchmark_data, scenario_data = self.jobs[job_name]
            job_file_path = self._job_file_path(job_name)
            if self.write_json_files:
                logger.info('Writing data for job "%s" to the filesystem...', job_name)
                job_file_path.parent.mkdir(parents=True, exist_ok=True)
                with job_file_path.open("w", encoding="utf-8") as json_file:
                    json.dump(benchmark_data, json_file, indent=4, default=str)
                for scenario_name, performance_data in scenario_data.items():
                    with self.scenario_file_path(job_name, scenario_name).open(
                        "w", encoding="utf-8"
                    ) as json_file:
                        json.dump(performance_data, json_file, indent=4, default=str)

                    if not len(performance_data) > 0:
                        continue

            if self.write_to_database:
                logger.info('Writing data for job "%s" to the database...', job_name)
                if self.update_db or self.purge_db:
                    self.database.delete_job(job_name=job_name)
                if self.purge_db:
                    continue
                # Scenarios read back from the database are stored already.
                new_scenario_data = {
                    scenario_name: performance_data
                    for scenario_name, performance_data in scenario_data.items()
                    if performance_data and self._scenario_on_disk(job_name, scenario_name)
                }
                if not new_scenario_data:
                    continue
                job_endtime = (
                    Datetime.fromisoformat(str(_ts))
                    if (_ts := benchmark_data.get("end_time", benchmark_data.get("datetime")))
                    else Datetime.now()
                )
                job_starttime = (
                    Datetime.fromisoformat(str(_ts))
                    if (_ts := benchmark_data.get("start_time"))
                    else min(
                        Datetime.fromisoformat(str(performance_data[0].get("time", "")))
                        for performance_data in new_scenario_data.values()
                    )
                )
                db_job_name = job_name
                if not (self.update_db or self.append_db):
                    db_job_name = self.database.job_run_name(job_name, job_endtime)
                    if db_job_name != job_name:
                        logger.info('Storing job "%s" as "%s".', job_name, db_job_name)
                for scenario_name, performance_data in new_scenario_data.items():
                    if self.append_db:
                        self.database.delete_test(job_name=job_name, scenario_name=scenario_name)
                    self.database.write_scenario_data(
                        job_name=db_job_name,
                        job_starttime=job_starttime,
                        job_endtime=job_endtime,
                        product_release=self.args.product_release,
                        scenario_name=scenario_name,
                        test_starttime=Datetime.fromisoformat(
                            str(performance_data[0].get("time", ""))
                        ),
                        test_endtime=Datetime.fromisoformat(
                            str(performance_data[-1].get("time", ""))
                        ),
                        benchmark_data=benchmark_data,
                        performance_data=performance_data,
                    )

    @staticmethod
    def _get_mean_value(measurements: MeasurementsList, metric_name: str) -> float:
        """
        Compute the arithmetic mean for a specified metric across a list of measurement records.

        Parameters:
            measurements : MeasurementsList
                Iterable / list of measurement rows containing the target metric.
            metric_name : str
                The key/name of the metric to extract from each measurement row.

        Returns:
            float
                The mean (floating-point) value of the metric across all measurements.
                Returns 0.0 if the input list is empty.
        """
        values: list[float] = [float(str(row[metric_name])) for row in measurements]
        return fmean(values or [0])

    def _calculate_baseline(self, scenario_name: str) -> AverageValues:
        """
        Compute average (baseline) metrics for a given benchmark scenario across all loaded jobs.

        This method iterates over all jobs, searches its benchmark list for the specified scenario
        and aggregates mean values for the execution time, the CPU usage and the memory usage.

        If a scenario is missing in a job, an error is logged and that job is skipped.
        If no values are collected for a metric, its baseline defaults to 0 (via fmean([0])).

        Parameters:
            scenario_name : str
                The name of the benchmark scenario to aggregate across all jobs.

        Returns:
                AverageValues
        """
        time_averages: list[float] = []
        cpu_averages: list[float] = []
        mem_averages: list[float] = []
        for job_name, job in self.jobs.items():
            if not isinstance(benchmarks := job[0]["benchmarks"], list):
                continue
            benchmark = next((_ for _ in benchmarks if _["name"] == scenario_name), None)
            if not benchmark:
                logger.warning('Scenario "%s" not found in job "%s"!', scenario_name, job_name)
                continue
            time_averages.append(benchmark["stats"]["mean"])
            if scenario_name not in job[1]:
                continue
            if not (measurements := job[1][scenario_name]):
                continue
            cpu_averages.append(self._get_mean_value(measurements, self.cpu_usage_metric))
            mem_averages.append(self._get_mean_value(measurements, self.memory_usage_metric))
        time_baseline = fmean(time_averages) if time_averages else 0.0
        cpu_baseline = fmean(cpu_averages) if cpu_averages else 0.0
        mem_baseline = fmean(mem_averages) if mem_averages else 0.0

        return AverageValues(*(time_baseline, cpu_baseline, mem_baseline))

    def _current_averages(self, scenario_name: str) -> AverageValues | None:
        """
        Return averaged performance metrics for a given benchmark scenario of the most recent job.

        If the benchmarks collection is not a list, or the named scenario is not present,
        the method returns None.

        Parameters:
            scenario_name : str
                    The exact benchmark scenario name to search for in the most recent job.

        Returns:
            AverageValues | None
                    An AverageValues instance containing (time_avg, cpu_avg, mem_avg) if the
                    scenario is found; otherwise None.
        """
        job = self.jobs[self.job_names[-1]]
        benchmarks = job[0]["benchmarks"]
        if not isinstance(benchmarks, list):
            return None
        benchmark = next((_ for _ in benchmarks if _["name"] == scenario_name), None)
        if not benchmark:
            return None
        time_avg = benchmark["stats"]["mean"]
        cpu_avg = self._get_mean_value(job[1][scenario_name], self.cpu_usage_metric)
        mem_avg = self._get_mean_value(job[1][scenario_name], self.memory_usage_metric)

        return AverageValues(*(time_avg, cpu_avg, mem_avg))

    @staticmethod
    def _skipped_scenario(
        scenario_name: str,
        baseline_name: str,
        skipped_scenarios: list[SkippedScenario],
    ) -> bool:
        """
        Check if a scenario should be skipped based on pattern matching and an optional condition.

        Args:
            scenario_name: The name of the scenario to check.
            baseline_name: The name of the baseline being evaluated.
            skipped_scenarios: A list of SkippedScenario objects.

        Returns:
            True if the scenario should be skipped, False otherwise.
        """
        for skipped_scenario in skipped_scenarios:
            if re.fullmatch(skipped_scenario.pattern, scenario_name) and skipped_scenario.condition:
                logger.info(
                    "Ignoring baseline %s scenario %s due to %s.",
                    baseline_name,
                    scenario_name,
                    skipped_scenario.reason,
                )
                return True
        return False

    def validate_performance_baselines(self) -> list[BaselineAlert]:
        """
        Validate current performance metrics against calculated baselines for each test scenario.

        For every scenario the method retrieves the current averaged metrics (time, CPU, memory)
        and a computed baseline, then compares them using a fixed overshoot tolerance (+10%).

        An alert is generated when any of the following averaged metrics exceeds its baseline by
        more than the tolerance percentage:
            - Execution time (avg_time)
            - CPU usage (avg_cpu)
            - Memory usage (avg_mem)

        If no current data (averages) are available for a scenario, a non-failing alert is
        added: the scenario is reported, but a missing measurement is not a regression.

        Returns:
            list[BaselineAlert]
                A list of alerts in scenario order. The list is empty if all scenarios
                are within tolerated performance bounds.
        """
        cpu_tolerance = self.args.cpu_tolerance
        mem_tolerance = self.args.mem_tolerance
        runtime_tolerance = self.args.runtime_tolerance
        baseline_offset = self.args.baseline_offset
        baseline_name = {0: "weekly", 30: "monthly", 365: "yearly"}.get(
            baseline_offset, f"{baseline_offset}d"
        )
        baseline_date = date.today() - timedelta(days=baseline_offset)

        skipped_scenarios = [
            SkippedScenario(pattern="test_performance_piggyback", reason="CMK-27171"),
            SkippedScenario(
                pattern="test_performance_ui_response_.*",
                reason="scenario changes on 2026-02-06",
                condition=baseline_date < date(2026, 2, 6),
            ),
        ]

        alerts: list[BaselineAlert] = []
        for scenario_name in self.scenario_names:
            if not scenario_name.startswith("test_"):
                continue
            if self._skipped_scenario(scenario_name, baseline_name, skipped_scenarios):
                continue

            msg_prefix = f"Scenario {scenario_name}: "
            msg_suffix = (
                f"; tolerance: +{cpu_tolerance}% CPU"
                f", +{mem_tolerance}% memory"
                f", +{runtime_tolerance}% time)"
            )
            averages = self._current_averages(scenario_name)
            if not averages:
                alerts.append(
                    BaselineAlert(
                        f"{msg_prefix}Missing data! Test aborted or skipped?", is_failure=False
                    )
                )
                continue
            baseline = self._calculate_baseline(scenario_name)
            if averages.avg_time > baseline.avg_time * (100 + runtime_tolerance) / 100:
                overshoot = round((averages.avg_time / baseline.avg_time) * 100 - 100, 2)
                msg = (
                    f"Execution time baseline {baseline_name} exceeded by {overshoot}% "
                    f"(baseline: {round(baseline.avg_time, 2)};"
                    f" actual: {round(averages.avg_time, 2)}"
                )

                alerts.append(BaselineAlert(f"{msg_prefix}{msg}{msg_suffix}"))
            if averages.avg_cpu > baseline.avg_cpu * (100 + cpu_tolerance) / 100:
                overshoot = round((averages.avg_cpu / baseline.avg_cpu) * 100 - 100, 2)
                msg = (
                    f"CPU usage baseline {baseline_name} exceeded by {overshoot}% "
                    f"(baseline: {round(baseline.avg_cpu, 2)}%;"
                    f" actual: {round(averages.avg_cpu, 2)}%"
                )
                alerts.append(BaselineAlert(f"{msg_prefix}{msg} {msg_suffix}"))
            if averages.avg_mem > baseline.avg_mem * (100 + mem_tolerance) / 100:
                overshoot = round((averages.avg_mem / baseline.avg_mem) * 100 - 100, 2)
                msg = (
                    f"Memory usage baseline {baseline_name} exceeded by {overshoot}% "
                    f"(baseline: {round(baseline.avg_mem, 2)}%;"
                    f" actual: {round(averages.avg_mem, 2)}%"
                )
                alerts.append(BaselineAlert(f"{msg_prefix}{msg}{msg_suffix}"))
        return alerts

    def create_ticket(self, summary: str, description: str) -> None:
        """
        Create an alert ticket by POSTing summary and description to the Jira server.

        This helper builds a JSON payload with the given summary and description and creates
        a ticket from it via the Jira API.

        Parameters:
            summary (str): Short, human‑readable title for the alert.
            description (str): Detailed description / context for the alert.
        """
        jira_issue = {
            "project": {"key": "CMK"},
            "summary": summary,
            "description": description,
            "customfield_11500": {"value": "QA"},  # cf[11500] = "Developer Team"
            "customfield_10106": 3,  # cf[10106] = "Story Points"
            "issuetype": {"name": "Task"},
        }
        jira_client = JIRA(
            server=self.jira_url,
            token_auth=self.jira_token,
        )
        jira_client.create_issue(jira_issue)


def main() -> None:
    """
    Runs the CLI application for performance test plotting.

    This function initializes the PerftestPlot application with parsed command-line arguments,
    checks for the presence of benchmark jobs, writes performance data, generates graph files
    if requested, and prints the output directory.

    Raises:
        SystemExit: If no benchmark jobs are provided.
    """
    rc = 0
    args = parse_args()
    logger.setLevel(args.log_level)
    # The modules this script imports log under the package's name.
    logging.getLogger("tests.performance.reporting").setLevel(args.log_level)
    app = PerftestPlot(args=args)
    if len(app.jobs) == 0:
        print(
            "Please provide one or more valid performance test benchmark jobs!\n\n"
            f'Run "{Path(__file__).name} --help" for more details.'
        )
        sys_exit()
    logger.info("Active jobs: %s", ", ".join(list(app.jobs.keys())))

    app.write_performance_data()

    if app.write_graph_files:
        graphs = PerformanceGraphs(
            jobs=app.jobs,
            job_names=app.job_names,
            scenario_names=app.scenario_names,
            cpu_usage_metric=app.cpu_usage_metric,
            memory_usage_metric=app.memory_usage_metric,
        )
        graphs.plot_benchmark_graph(app.output_dir / "benchmark.png")
        graphs.plot_resource_graph(app.output_dir / "resources.png")
        graphs.plot_resource_graph(app.output_dir / "history.resources.png", history=True)

    if app.validate_baselines:
        alerts = app.validate_performance_baselines()
        summary = f"Validate performance test {list(app.jobs.keys())[-1]}"
        messages = [alert.message for alert in alerts]
        description = (f"\n  {'\n  '.join(messages)}") if messages else "PASSED!"
        print(f"{summary}: {description}")
        failures = [alert for alert in alerts if alert.is_failure]
        if app.alert_on_failure and failures:
            app.create_ticket(summary=summary, description=description)
        if failures and app.warn_only:
            print("Baseline validation failed, but --warn-only was given: not failing the job.")
        elif failures:
            rc = 2

    print(app.output_dir)
    sys_exit(rc)


if __name__ == "__main__":
    main()

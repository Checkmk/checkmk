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
        2.5.0-2025.09.10.ultimate
"""

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

import argparse
import json
import logging
import re
from collections.abc import Callable, Sequence
from datetime import date, timedelta
from datetime import datetime as Datetime
from os import getenv
from pathlib import Path
from statistics import fmean
from sys import exit as sys_exit
from typing import get_args, NamedTuple

import psycopg
from jira import JIRA
from matplotlib import colormaps, gridspec, pyplot

from tests.performance.reporting.performance_db import (
    Measurements,
    MeasurementsList,
    PerformanceDb,
    SslMode,
)

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


class PerftestPlot:
    PerformanceData = dict[str, tuple[Measurements, dict[str, MeasurementsList]]]

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
        self.colormap = "tab10"

    @staticmethod
    def _px(val: int) -> int:
        """Return a figsize value given in pixels"""
        return 1 / pyplot.rcParams["figure.dpi"] * val

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

    def _plottable_benchmark_data(
        self, scenario_name: str
    ) -> tuple[list[float | None], list[float | None]]:
        """
        Extracts plottable mean and standard deviation values for a given benchmark scenario.

        Args:
            scenario_name (str): The name of the benchmark scenario to extract data for.

        Returns:
            tuple[list[int | float], list[int | float]]:
                - A list of mean values for the specified scenario across all jobs.
                - A list of standard deviation values for the specified scenario across all jobs.
                Note: If a job does not contain scenario data, None is appended for both values.
        """
        values: list[float | None] = []
        err_values: list[float | None] = []
        for _, benchmark_data in self.jobs.items():
            if not (
                isinstance(benchmark_data[0], dict)
                and isinstance(benchmark_data[0]["benchmarks"], list)
            ):
                continue
            if benchmark := next(
                (
                    _benchmark
                    for _benchmark in benchmark_data[0]["benchmarks"]
                    if isinstance(_benchmark, dict) and str(_benchmark["name"]) == scenario_name
                ),
                None,
            ):
                values.append(benchmark["stats"]["mean"])
                err_values.append(benchmark["stats"]["stddev"])
            else:
                values.append(None)
                err_values.append(None)
        return values, err_values

    def plot_benchmark_graph(self, graph_file: Path) -> None:
        """
        Generates and saves a benchmark graph for each scenario.

        For each scenario, this method retrieves benchmark values and error values, formats the
        labels, and plots an error bar graph showing execution times per job. The graph includes
        error bars, grid lines, and custom axis labels. The resulting plot is saved as an image
        file in the specified location.

        Args:
            graph_file (Path): The file path of the output graph image.

        Returns:
            None
        """
        # Define a color palette for better visual distinction
        colors = colormaps.get_cmap(self.colormap)(range(8))

        for scenario_name in self.scenario_names:
            raw_values, raw_err_values = self._plottable_benchmark_data(scenario_name)
            if not (raw_values and raw_err_values) or all(_ in (0, None) for _ in raw_values):
                continue
            graph_file_path = graph_file.parent / f"{scenario_name}.{graph_file.name}"
            logger.info('Writing graph "%s"...', graph_file_path)
            alternate = len(self.jobs) > 6
            max_value = 0
            values: list[float] = []
            err_values: list[float] = []
            names: list[str] = []
            for idx, benchmark in enumerate(self.jobs):
                value = raw_values[idx]
                err_value = raw_err_values[idx]
                if value is None or err_value is None:
                    continue
                max_value = int(max(value + err_value + 1, max_value))
                name = f"{benchmark}\n{round(value, 1)}s (+/-{round(err_value, 1)}s)"
                if alternate and idx % 2 == 1:
                    name = f"\n\n{name}"
                values.append(value)
                err_values.append(err_value)
                names.append(name)

            fig, times = pyplot.subplots(1, figsize=(self._px(1920), self._px(1080)))

            # Improve overall figure styling
            fig.suptitle(
                f"Benchmark: {scenario_name} (single execution)", fontsize=16, fontweight="bold"
            )
            fig.patch.set_facecolor("white")

            # Create error bar plot with improved styling
            times.errorbar(
                x=names,
                y=values,
                yerr=err_values,
                fmt="o",
                capsize=5,
                capthick=2,
                elinewidth=2,
                markersize=8,
                linewidth=2,
                color=colors[0],
                markerfacecolor=colors[1],
                markeredgecolor=colors[0],
                alpha=0.8,
            )

            # Improve axis styling
            times.set_ylim(ymin=0, ymax=max_value * 1.1)
            times.set_ylabel("Time (s)", fontsize=12)
            times.set_xlabel("Job", fontsize=12)
            times.set_yscale("linear")

            # Improve grid styling
            times.grid(True, which="major", axis="y", linestyle="-", alpha=0.3, linewidth=0.8)
            times.grid(True, which="minor", axis="y", linestyle=":", alpha=0.2, linewidth=0.5)
            times.set_yticks(ticks=range(0, max_value, max(1, max_value // 10)), minor=False)
            times.set_yticks(ticks=range(0, max_value, max(1, max_value // 20)), minor=True)

            # Style the axes and background
            times.set_facecolor("#f8f9fa")
            times.spines["top"].set_visible(False)
            times.spines["right"].set_visible(False)
            times.spines["left"].set_color("#cccccc")
            times.spines["bottom"].set_color("#cccccc")
            times.tick_params(axis="both", which="major", labelsize=10)
            times.tick_params(axis="x", rotation=0)

            # Add subtle data point annotations for better readability
            for i, (name, value, err) in enumerate(zip(names, values, err_values)):
                times.annotate(
                    f"{value:.1f}s",
                    (i, value + err + max_value * 0.02),
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    alpha=0.7,
                    fontweight="bold",
                )

            # Save with high DPI for better quality
            pyplot.savefig(graph_file_path, dpi=300, facecolor="white", edgecolor="none")
            pyplot.close()

    @staticmethod
    def _plottable_resource_data(
        statistics: MeasurementsList, metric_name: str
    ) -> tuple[list[float], list[float]]:
        """
        Extracts and prepares resource usage data for plotting from a list of measurement values.

        Args:
            statistics (MeasurementsList): A list of measurement dictionaries containing timestamp
                and resource usage data.
            metric_name (str): The name used to identify the specific metric.

        Returns:
            tuple[list[float], list[float]]:
                - A list of durations (in seconds) between each timestamp, suitable for use as the
                  x-axis in a plot.
                - A list of resource usage measurements (as floats), suitable for use as the
                  y-axis in a plot.

        Notes:
            - Only statistics that are dictionaries and contain valid timestamp and resource usage
              values are processed.
            - The durations are calculated as evenly spaced intervals between the first and last
              timestamps.
            - Resource usage values are converted to floats for consistency.
        """

        def get_durations(timestamps: list[str]) -> list[float]:
            """
            Calculates evenly spaced durations between the first and last timestamps.

            Args:
                timestamps (list[str]): List of ISO format timestamp strings.

            Returns:
                list[float]: List of durations (in seconds) from the start time, evenly spaced
                    between the first and last timestamp.
            """
            start_time = Datetime.fromisoformat(timestamps[0])
            end_time = Datetime.fromisoformat(timestamps[-1])
            duration = end_time - start_time
            interval = round(duration.total_seconds() / len(timestamps), 1)
            return [i * interval for i in range(len(timestamps))]

        timestamps: list[str] = []
        measurements: list[float] = []
        for stats in statistics:
            if not isinstance(stats, dict):
                continue
            timestamp = str(stats["time"])
            raw_value = stats[metric_name]
            if isinstance(raw_value, int | float | str):
                value = float(raw_value)
                timestamps.append(timestamp)
                measurements.append(value)
        return get_durations(timestamps), measurements

    def plot_resource_graph(self, graph_file: Path, history: bool = False) -> None:
        """
        Plots resource usage graphs (CPU, memory) for each scenario and saves them as image files.

        For each scenario, this method creates a figure with two subplots:
        one for CPU usage and one for memory usage. It iterates over all selected jobs, extracts
        the relevant statistics, and plots the resource usage over time. The average usage is also
        plotted as a dashed line. Each plot is labeled with the job name and its average usage.

        The resulting graphs are saved to the specified `graph_file` location, with filenames
        including the scenario name.

        Args:
            graph_file (Path): The path to save the generated graph images.
            history (bool): A historical comparison graph is plotted.

        Returns:
            None
        """
        # Define a color palette for better visual distinction
        colors = colormaps.get_cmap(self.colormap)(range(len(self.jobs)))
        pyplot.subplots_adjust(hspace=100)
        for scenario_name in self.scenario_names:
            if scenario_name == "teardown_central_site":
                continue
            gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1], hspace=0.3)
            fig = pyplot.figure(figsize=(self._px(1920), self._px(1080)))
            ax_cpu = fig.add_subplot(gs[0])
            ax_mem = fig.add_subplot(gs[1])

            # Improve overall figure styling
            graph_suffix = graph_file.name.removeprefix(scenario_name).removesuffix(
                f"resources{graph_file.suffix}"
            )
            subplot_title = f"{scenario_name}.{graph_suffix}".removesuffix(".")
            fig.suptitle(
                f"Resource usage: {subplot_title}",
                fontsize=16,
                fontweight="bold",
            )
            fig.set_size_inches(self._px(1920), self._px(1080))
            fig.set_linewidth(1.0)
            fig.patch.set_facecolor("white")

            graph_file_path = graph_file.parent / f"{scenario_name}.{graph_file.name}"
            logger.info('Writing graph "%s"...', graph_file_path)

            xmax = 60
            jobs = self.jobs if history else {self.job_names[-1]: self.jobs[self.job_names[-1]]}
            for job_idx, (job_name, data) in enumerate(jobs.items()):
                statistics = data[1].get(scenario_name, [])
                color = colors[job_idx % len(colors)]

                for subplot, metric_name, title in [
                    (ax_cpu, self.cpu_usage_metric, "CPU"),
                    (ax_mem, self.memory_usage_metric, "Virtual Memory"),
                ]:
                    if not statistics:
                        continue

                    durations, values = self._plottable_resource_data(statistics, metric_name)
                    xmax = int(durations[-1]) if durations and durations[-1] > xmax else xmax
                    average = fmean(values or [0])

                    # Plot main line with improved styling
                    subplot.plot(
                        durations,
                        values,
                        label=f"{job_name} (avg={round(average, 1)}%)",
                        alpha=0.8,
                        linewidth=1.0,
                        color=color,
                    )

                    # Draw average line with better styling
                    subplot.axhline(
                        y=average, linestyle="--", color=color, alpha=0.6, linewidth=1.5
                    )

                    # Improve subplot styling
                    subplot.set_title(title, fontsize=14, fontweight="bold", pad=20)
                    subplot.set_ylabel("Usage (%)", fontsize=12)
                    subplot.set_xlabel("Time (seconds)", fontsize=12)
                    subplot.set_ylim(0, 100)
                    subplot.set_xlim(0, xmax)

                    # Add grid for better readability
                    subplot.grid(True, alpha=0.3, linestyle="-", linewidth=0.5)
                    subplot.set_facecolor("#f8f9fa")

                    # Improve legend styling
                    legend = subplot.legend(
                        loc="upper right", frameon=True, fancybox=True, shadow=True, fontsize=10
                    )
                    legend.get_frame().set_facecolor("white")
                    legend.get_frame().set_alpha(0.9)

                    # Style the axes
                    subplot.tick_params(axis="both", which="major", labelsize=10)
                    subplot.spines["top"].set_visible(False)
                    subplot.spines["right"].set_visible(False)
                    subplot.spines["left"].set_color("#cccccc")
                    subplot.spines["bottom"].set_color("#cccccc")

            # Save with high DPI for better quality
            pyplot.savefig(
                graph_file_path,
                dpi=300,
                facecolor="white",
                edgecolor="none",
            )
            pyplot.close()

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
        default="2.5.0",
        help="The default branch version for jobs (default: %(default)s).",
    )
    parser.add_argument(
        "--edition",
        dest="edition",
        type=str,
        default="pro",
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
        help="The product release of the stored jobs, e.g. 2.5.0-2026.11.16 (default: none).",
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
        app.plot_benchmark_graph(app.output_dir / "benchmark.png")
        app.plot_resource_graph(app.output_dir / "resources.png")
        app.plot_resource_graph(app.output_dir / "history.resources.png", history=True)

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

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
    python perftest_plot.py [options] <job_names>

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
    --validate-baselines     Whether to perform baseline validation.
    --alert-on-failure       Whether to alert on failed baseline validation.
    --log-level              Set the log level for the application.
    job_names                List of job names to process.

Example:
    python perftest_plot.py --dbhost qa.lan.checkmk.net 2.5.0-2025.09.10.cce
"""

import argparse
import json
import logging
import re
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime as Datetime
from os import getenv
from pathlib import Path
from statistics import fmean
from sys import exit as sys_exit
from typing import NamedTuple

import psycopg
from jira import JIRA
from matplotlib import pyplot

logging.basicConfig()
logger = logging.getLogger(__name__)

Measurements = Mapping[str, object]
MeasurementsList = list[Measurements]


class AverageValues(NamedTuple):
    avg_time: float
    avg_cpu: float
    avg_mem: float


class JobDetails(NamedTuple):
    """
    Represents details about a performance test job.

    Attributes:
        job_id (int): Unique identifier for the job.
        job_name (str): Name of the job.
        start_timestamp (Datetime): Timestamp when the job started.
        end_timestamp (Datetime): Timestamp when the job ended.
        product_release (str): Product release version associated with the job.
        system_name (str): Name of the system where the job ran.
        system_release (str): Release version of the system.
        system_machine (str): Machine type of the system.
        host_name (str): Hostname where the job was executed.
    """

    job_id: int
    job_name: str
    start_timestamp: Datetime
    end_timestamp: Datetime
    product_release: str
    system_name: str
    system_release: str
    system_machine: str
    host_name: str


class ScenarioDetails(NamedTuple):
    """
    Represents the details of a test scenario.

    Attributes:
        scenario_id (int): Unique identifier for the scenario.
        scenario_name (str): Name of the scenario.
        scenario_description (str): Description of the scenario.
    """

    scenario_id: int
    scenario_name: str
    scenario_description: str


class TestDetails(NamedTuple):
    """
    Represents the details of a performance test.

    Attributes:
        test_id (int): Unique identifier for the test.
        job_id (int): Identifier for the job associated with the test.
        scenario_id (int): Identifier for the scenario under which the test was run.
        start_timestamp (Datetime): Timestamp marking the start of the test.
        end_timestamp (Datetime): Timestamp marking the end of the test.
    """

    test_id: int
    job_id: int
    scenario_id: int
    start_timestamp: Datetime
    end_timestamp: Datetime


class PerformanceDb:
    """
    PerformanceDb provides an interface for storing and retrieving performance test data
    in a PostgreSQL database.

    This class manages jobs, scenarios, tests, measurements, and benchmark statistics,
    supporting insertion and querying operations for performance testing workflows.

    Attributes:
        dbname (str): Name of the database to connect to.
        user (str): Database user.
        host (str): Database host address.
        port (int): Database port number.
        dsn (str): Data Source Name for PostgreSQL connection.
        connection: Active psycopg connection to the database.
    """

    def __init__(
        self,
        sslrootcert: Path,
        sslcert: Path,
        sslkey: Path,
        sslmode: str = "require",
        dbname: str = "performance",
        user: str = "performance",
        host: str = "qa.lan.checkmk.net",
        port: int = 5432,
    ):
        """
        Initializes a database connection for performance testing.

        Args:
            dbname (str, optional): Name of the database. Defaults to "performance".
            user (str, optional): Database user name. Defaults to "performance".
            host (str, optional): Database host address. Defaults to "localhost".
            port (int, optional): Database port number. Defaults to 5432.

        Attributes:
            dbname (str): Name of the database.
            user (str): Database user name.
            host (str): Database host address.
            port (int): Database port number.
            dsn (str): Data Source Name for the database connection.
            connection: Active connection to the database.
        """
        self.dbname = dbname
        self.user = user
        self.host = host
        self.port = port
        self.sslmode = sslmode
        self.sslrootcert = sslrootcert
        self.sslcert = sslcert
        self.sslkey = sslkey
        self.dsn = (
            "sslmode=%s dbname=%s user=%s host=%s port=%s sslrootcert=%s sslcert=%s sslkey=%s"
            % (
                self.sslmode,
                self.dbname,
                self.user,
                self.host,
                self.port,
                self.sslrootcert,
                self.sslcert,
                self.sslkey,
            )
        )
        self.connection = psycopg.connect(self.dsn, autocommit=True)

    @contextmanager
    def cursor(self) -> Iterator[psycopg.cursor.Cursor]:
        """Return an active cursor in a new autocommit connection."""
        with self.connection.cursor() as cursor:
            yield cursor

    def add_job(
        self,
        job_name: str,
        start_timestamp: Datetime,
        end_timestamp: Datetime,
        product_release: str,
        system_name: str,
        system_release: str,
        system_machine: str,
        host_name: str,
    ) -> int:
        """Add job details to the database if they do not exist already.

        Returns the ID of the new or existing job entry.
        """
        try:
            return self.get_job(job_name=job_name)[0]
        except ValueError:
            with self.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO jobs(
                        job_name,
                        start_timestamp,
                        end_timestamp,
                        product_release,
                        system_name,
                        system_release,
                        system_machine,
                        host_name
                    )
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING job_id
                    """,
                    (
                        job_name,
                        start_timestamp,
                        end_timestamp,
                        product_release,
                        system_name,
                        system_release,
                        system_machine,
                        host_name,
                    ),
                )
                job_id = result_record[0] if (result_record := cursor.fetchone()) else None
            if job_id is None:
                raise ValueError(f'Error adding job "{job_name}"!')
            return job_id

    def get_job(self, job_name: str) -> JobDetails:
        """
        Retrieves job details for a given job name from the database.

        Args:
            job_name (str): The name of the job to retrieve.

        Returns:
            JobDetails: An object containing the details of the retrieved job.

        Raises:
            ValueError: If no job with the specified name is found in the database.
        """
        with self.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    job_id,
                    job_name,
                    start_timestamp,
                    end_timestamp,
                    product_release,
                    system_name,
                    system_release,
                    system_machine,
                    host_name
                FROM jobs
                WHERE job_name = %s
                """,
                (job_name,),
            )
            job_details = cursor.fetchone()
        if job_details is None:
            raise ValueError(f'Error retrieving job "{job_name}"!')
        return JobDetails(*job_details)

    def check_job(self, job_name: str) -> bool:
        """
        Determines whether a job with the specified name exists.

        Args:
            job_name (str): The name of the job to check.

        Returns:
            bool: True if the job exists, False otherwise.

        Logs:
            Errors encountered during job lookup are logged.
        """
        try:
            return self.get_job(job_name=job_name)[0] is not None
        except ValueError as excp:
            print(excp)
            return False

    def add_scenario(self, scenario_name: str, scenario_description: str | None = None) -> int:
        """
        Adds a scenario to the database if it does not already exist.

        If the scenario with the given name exists, returns its ID.
        Otherwise, inserts a new scenario with the provided name and optional description,
        and returns the newly created scenario's ID.

        Args:
            scenario_name (str): The name of the scenario to add or retrieve.
            scenario_description (str | None, optional): An optional description for the scenario.

        Returns:
            int: The ID of the existing or newly created scenario.

        Raises:
            ValueError: If there is an error adding the scenario to the database.
        """
        try:
            return self.get_scenario(scenario_name=scenario_name)[0]
        except ValueError:
            with self.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO scenarios(
                        scenario_name,
                        scenario_description
                    )
                    VALUES(%s,%s)
                    RETURNING scenario_id
                    """,
                    (scenario_name, scenario_description),
                )
                scenario_id = result_record[0] if (result_record := cursor.fetchone()) else None
            if scenario_id is None:
                raise ValueError(f'Error adding scenario "{scenario_name}"!')
            return scenario_id

    def get_scenario(self, scenario_name: str) -> ScenarioDetails:
        """
        Retrieves the details of a scenario from the database by its name.

        Args:
            scenario_name (str): The name of the scenario to retrieve.

        Returns:
            ScenarioDetails: An object containing the scenario's ID, name, and description.

        Raises:
            ValueError: If no scenario with the given name is found in the database.
        """
        with self.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    scenario_id,
                    scenario_name,
                    scenario_description
                FROM scenarios
                WHERE scenario_name = %s
                """,
                (scenario_name,),
            )
            scenario_details = cursor.fetchone()
        if scenario_details is None:
            raise ValueError(f'Error retrieving scenario "{scenario_name}"!')
        return ScenarioDetails(*scenario_details)

    def get_scenario_names(self) -> list[str]:
        """
        Retrieves all unique scenario names from the 'scenarios' table in the database.

        Returns:
            list[str]: A list containing the distinct scenario names.
        """
        with self.cursor() as cursor:
            cursor.execute("""SELECT DISTINCT scenario_name FROM scenarios""")
            scenario_names = [_[0] for _ in cursor.fetchall()]
        return scenario_names

    def add_test(
        self, job_id: int, scenario_id: int, start_timestamp: Datetime, end_timestamp: Datetime
    ) -> int:
        """
        Adds a test entry to the database if it does not already exist.

        Parameters:
            job_id (int): The ID of the job associated with the test.
            scenario_id (int): The ID of the scenario associated with the test.
            start_timestamp (Datetime): The start timestamp of the test.
            end_timestamp (Datetime): The end timestamp of the test.

        Returns:
            int: The ID of the newly created or existing test entry.

        Raises:
            ValueError: If the test cannot be added to the database.

        """
        try:
            return self.get_test(job_id=job_id, scenario_id=scenario_id)[0]
        except ValueError:
            with self.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO tests(
                        job_id,
                        scenario_id,
                        start_timestamp,
                        end_timestamp
                    )
                    VALUES(%s,%s,%s,%s)
                    RETURNING test_id
                    """,
                    (job_id, scenario_id, start_timestamp, end_timestamp),
                )
                test_id = result_record[0] if (result_record := cursor.fetchone()) else None
            if test_id is None:
                raise ValueError(f'Error adding test "{scenario_id}" to job "{job_id}"!')
            return test_id

    def get_test(self, job_id: int, scenario_id: int) -> TestDetails:
        """
        Retrieve the details of a specific test from the database based on job and scenario IDs.

        Args:
            job_id (int): The ID of the job associated with the test.
            scenario_id (int): The ID of the scenario associated with the test.

        Returns:
            TestDetails: An object containing the details of the test.

        Raises:
            ValueError: If no test details are found for the given job_id and scenario_id.
        """
        with self.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    test_id,
                    job_id,
                    scenario_id,
                    start_timestamp,
                    end_timestamp
                FROM tests
                WHERE job_id = %s AND scenario_id = %s""",
                (job_id, scenario_id),
            )
            test_details = cursor.fetchone()
        if test_details is None:
            raise ValueError(
                f'Test details for scenario "{scenario_id}" not found in job "{job_id}"!'
            )
        return TestDetails(*test_details)

    def write_measurements(self, test_id: int, measurements: MeasurementsList) -> None:
        """
        Inserts measurement data into the 'metrics' database table for a given test.

        Args:
            test_id (int): The identifier of the test to associate the measurements with.
            measurements (MeasurementsList): A list of dictionaries, each containing metric names
                and their corresponding values. Each dictionary must include a "time" key
                representing the measurement timestamp.

        Notes:
            - Each metric is inserted as a separate row in the 'metrics' table.
        """
        with self.cursor() as cursor:
            data = []
            for measurement in measurements:
                assert isinstance(measurement, dict)
                for metric_name in measurement:
                    if metric_name == "time":
                        continue
                    data.append(
                        (test_id, metric_name, measurement[metric_name], measurement["time"])
                    )
            cursor.executemany(
                """
                INSERT INTO metrics (
                    test_id,
                    metric_name,
                    measured_value,
                    measured_at
                )
                VALUES (%s,%s,%s,%s)
                """,
                data,
            )

    def write_benchmark_statistics(self, test_id: int, benchmark_statistics: Measurements) -> None:
        """
        Writes benchmark statistics to the database for a given test.

        Args:
            test_id (int): The identifier of the test for which statistics are recorded.
            benchmark_statistics (Measurements): A dictionary containing benchmark metrics and
                their values.

        Note:
            Any value types other than int and float are ignored.
        """
        write_benchmark_statistics: dict[str, int | float] = {
            key: val for key, val in benchmark_statistics.items() if isinstance(val, int | float)
        }
        if "data" in benchmark_statistics:
            assert isinstance(benchmark_statistics["data"], list)
            for i, value in enumerate(benchmark_statistics["data"]):
                write_benchmark_statistics[f"data{i}"] = value
        with self.cursor() as cursor:
            for metric_name, value in write_benchmark_statistics.items():
                cursor.execute(
                    """
                    INSERT INTO benchmarks (
                        test_id,
                        metric_name,
                        measured_value
                    )
                    VALUES (%s,%s,%s)
                    """,
                    (test_id, metric_name, value),
                )

    def read_benchmark_statistics(self, test_id: int) -> Measurements:
        """
        Reads benchmark statistics for a given test ID from the database.

        Fetches metric names and their measured values associated with the specified test ID,
        ignoring any values that are not of type int or float. The results are returned as a
        dictionary mapping metric names to their float values, sorted by metric name in ascending order.

        Args:
            test_id (int): The ID of the benchmark test to retrieve statistics for.

        Returns:
            Measurements: A dictionary containing metric names as keys and their corresponding float values.

        Note:
            Any value types other than int and float are ignored.
        """
        with self.cursor() as cursor:
            cursor.execute(
                """
                    SELECT metric_name, measured_value
                    FROM benchmarks
                    WHERE test_id = %s
                    ORDER BY metric_name ASC
                    """,
                (test_id,),
            )
            measurements: dict = {}
            while len(rows := cursor.fetchmany(100)) > 0:
                for row in rows:
                    metric_name, measured_value = row
                    measurements[metric_name] = float(measured_value)

        return measurements

    def read_measurements(self, test_id: int) -> MeasurementsList:
        """
        Retrieves and organizes measurement data for a given test ID from the database.

        Args:
            test_id (int): The ID of the test for which measurements are to be read.

        Returns:
            MeasurementsList: A list of dictionaries, each containing a 'time' key (timestamp)
            and metric name/value pairs for that time.

        Raises:
            AssertionError: If the database returns a 'measured_at' value that is not a Datetime instance,
            or if the internal data structures do not match expected types.
        """
        with self.cursor() as cursor:
            cursor.execute(
                """
                    SELECT metric_name, measured_at, measured_value
                    FROM metrics
                    WHERE test_id = %s
                    ORDER BY metric_name ASC, measured_at ASC
                    """,
                (test_id,),
            )
            raw_measurements: dict = {}
            while rows := cursor.fetchmany(100):
                for row in rows:
                    metric_name, measured_at, measured_value = row
                    assert isinstance(measured_at, Datetime)
                    if measured_at not in raw_measurements:
                        raw_measurements[measured_at] = {}
                    assert isinstance(raw_measurements[measured_at], dict)
                    raw_measurements[measured_at].update({metric_name: measured_value})

        measurements: MeasurementsList = []
        assert isinstance(measurements, list)
        for time, measurement in raw_measurements.items():
            measurements.append({"time": time} | measurement)

        return measurements

    def write_performance_data(
        self,
        job_name: str,
        job_starttime: Datetime,
        job_endtime: Datetime,
        scenario_name: str,
        test_starttime: Datetime,
        test_endtime: Datetime,
        benchmark_data: Measurements,
        performance_data: MeasurementsList,
    ) -> None:
        """
        Writes performance data and related metadata to the database.

        This method records job, scenario and test information, then stores associated performance
        measurements and benchmark statistics.

        Args:
            job_name (str): Name of the job.
            job_starttime (Datetime): Timestamp when the job started.
            job_endtime (Datetime): Timestamp when the job ended.
            scenario_name (str): Name of the test scenario.
            test_starttime (Datetime): Timestamp when the test started.
            test_endtime (Datetime): Timestamp when the test ended.
            benchmark_data (Measurements): Dictionary containing benchmark metadata and results.
            performance_data (MeasurementsList): List of measurement dictionaries for the test.

        Returns:
            None
        """
        if not (
            "machine_info" in benchmark_data
            and isinstance((machine_info := benchmark_data["machine_info"]), dict)
        ):
            machine_info = {}
        job_id = self.add_job(
            job_name=job_name,
            start_timestamp=job_starttime,
            end_timestamp=job_endtime,
            product_release="",
            system_name=str(machine_info.get("system", "")),
            system_release=str(machine_info.get("release", "")),
            system_machine=str(machine_info.get("machine", "")),
            host_name=str(machine_info.get("node", "")),
        )
        scenario_id = self.add_scenario(scenario_name)
        try:
            self.get_test(job_id=job_id, scenario_id=scenario_id)[0]
        except ValueError:
            test_id = self.add_test(
                job_id=job_id,
                scenario_id=scenario_id,
                start_timestamp=test_starttime,
                end_timestamp=test_endtime,
            )
            self.write_measurements(test_id=test_id, measurements=performance_data)
            assert isinstance(benchmarks := benchmark_data["benchmarks"], list)
            benchmark_statistics: Measurements | None = next(
                (_["stats"] for _ in benchmarks if _["name"] == scenario_name), None
            )
            if benchmark_statistics:
                self.write_benchmark_statistics(
                    test_id=test_id,
                    benchmark_statistics=benchmark_statistics,
                )


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
        validate_baselines (bool): Enable performance baseline validation.
        alert_on_failure (bool): Enable Jira alerter on baseline validation failure.
        sslmode (str): The SSL mode for the Postgres authentication.
        sslrootcert_var (str): The name of the environment variable that holds the root certificate.
        sslcert_var (str): The name of the environment variable that holds the Postgres certificate.
        sslkey_var (str): The name of the environment variable that holds the Postgres key.
        cert_folder (Path): The folder in which the certificate files are stored.
        jira_url (str): The URL of the Jira server.
        jira_token_var (str): The name of the environment variable that holds the Jira token.
        jira_token_path (Path): The path of file that holds the Jira token.
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
    validate_baselines: bool
    alert_on_failure: bool
    sslmode: str
    sslrootcert_var: str
    sslcert_var: str
    sslkey_var: str
    cert_folder: Path
    jira_url: str
    jira_token_var: str
    jira_token_path: Path
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
        self.root_dir = self.args.root_dir
        self.read_from_database = not self.args.skip_database_reads
        self.read_from_filesystem = not self.args.skip_filesystem_reads
        self.write_to_database = not self.args.skip_database_writes
        if self.args.dbhost and (self.read_from_database or self.write_to_database):
            sslrootcert, sslcert, sslkey = self.setup_db_certificates()
            try:
                self.database = PerformanceDb(
                    sslrootcert=sslrootcert,
                    sslcert=sslcert,
                    sslkey=sslkey,
                    sslmode=self.args.sslmode,
                    dbname=self.args.dbname,
                    user=self.args.dbuser,
                    host=self.args.dbhost,
                    port=self.args.dbport,
                )
                print("A connection was successfully established with the database!")
            except psycopg.OperationalError as excp:
                print(
                    f'Could not connect to database "{self.args.dbname}"; '
                    f"switching to filesystem mode!\n\n{excp}",
                )
                self.read_from_database = self.write_to_database = False
        else:
            print("Database access disabled; switching to filesystem mode!")
            self.read_from_database = self.write_to_database = False

        self.write_json_files = self.args.write_json_files and not self.args.skip_filesystem_writes
        self.write_graph_files = not (
            self.args.skip_graph_generation or self.args.skip_filesystem_writes
        )
        self.jira_url = self.args.jira_url
        self.jira_token = self.read_jira_token()
        self.alert_on_failure = self.args.alert_on_failure and self.jira_url and self.jira_token
        self.validate_baselines = self.args.validate_baselines or self.alert_on_failure
        self.job_names = self.read_job_names()
        self.scenario_names = self.read_scenario_names()
        self.jobs = self.read_performance_data()
        self.output_dir = self.args.output_dir or (
            self.job_file_path(self.job_names[-1]).parent if self.job_names else self.root_dir
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def px(val: int) -> int:
        """Return a figsize value given in pixels"""
        return 1 / pyplot.rcParams["figure.dpi"] * val

    @staticmethod
    def read_json(json_path: Path) -> Measurements | MeasurementsList | None:
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
            logger.error('File "%s" not found!', json_path)
        except (json.JSONDecodeError, OSError):
            logger.error('Can not parse JSON file "%s"!', json_path)
        return None

    def job_file_path(self, job_name: str) -> Path:
        """
        Returns the file path to the benchmark JSON file for a given job.

        Args:
            job_name (str): The name of the job.

        Returns:
            Path: The path to the benchmark.json file.
        """
        return self.root_dir / f"{job_name}/benchmark.json"

    def read_jira_token(self) -> str | None:
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

    def setup_db_certificates(self) -> tuple[Path, Path, Path]:
        """
        Set up PostgreSQL SSL certificates in the user's home directory.

        Creates a directory and writes three certificate files:
        - postgresql.crt: Client certificate (mode 644)
        - postgresql.key: Client private key (mode 600)
        - root.crt: Root CA certificate (mode 600)

        The certificate content is read from environment variables specified in
        self.args.sslcert_var, self.args.sslkey_var, and
        self.args.sslrootcert_var respectively.

        If the directory already exists, the setup is skipped.
        Any existing certificate files are removed before writing new ones.

        Prints status messages indicating setup progress and created files.

        Returns a tuple with the paths to the client cert, client key and root cert.
        """
        sslrootcert = self.args.cert_folder / "root.crt"
        sslcert = self.args.cert_folder / "postgresql.crt"
        sslkey = self.args.cert_folder / "postgresql.key"
        if not (self.args.cert_folder).exists():
            logger.info("Certificate setup...")
            self.args.cert_folder.mkdir(mode=750)
            sslrootcert.unlink(missing_ok=True)
            sslrootcert.write_text(getenv(self.args.sslrootcert_var, ""))
            sslrootcert.chmod(mode=600)
            sslcert.unlink(missing_ok=True)
            sslcert.write_text(getenv(self.args.sslcert_var, ""))
            sslcert.chmod(mode=644)
            sslkey.unlink(missing_ok=True)
            sslkey.write_text(getenv(self.args.sslkey_var, ""))
            sslkey.chmod(mode=600)
            cert_files = ", ".join(_.name for _ in self.args.cert_folder.glob("*"))
            if cert_files:
                logger.info("Certificate files created: %s", cert_files)
            else:
                logger.error("Certificate setup failed!")
        return (
            sslrootcert,
            sslcert,
            sslkey,
        )

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
        for scenario_name in self.scenario_names:
            raw_values, raw_err_values = self._plottable_benchmark_data(scenario_name)
            if not (raw_values and raw_err_values) or all(_ == 0 for _ in raw_values):
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

            fig, times = pyplot.subplots(1)
            fig.suptitle(f"Execution time: {scenario_name}")
            fig.set_size_inches(self.px(1920), self.px(1080))
            times.errorbar(x=names, y=values, yerr=err_values)
            times.set_ylim(ymin=0)
            times.set_ylabel("time (s)")
            times.set_yscale("linear")
            times.set_yticks(ticks=range(0, max_value, 1), minor=True)
            times.grid(visible=True, which="both", axis="y", linestyle="dotted")
            times.set_xlabel("runtime per release (single iteration)")
            pyplot.savefig(graph_file_path)
            pyplot.close()

    @staticmethod
    def _plottable_resource_data(
        statistics: MeasurementsList, section: str, indicator: str
    ) -> tuple[list[float], list[float]]:
        """
        Extracts and prepares resource usage data for plotting from a list of measurement values.

        Args:
            statistics (MeasurementsList): A list of measurement dictionaries containing timestamp
                and resource usage data.
            section (str): The section name used to identify the resource.
            indicator (str): The indicator name used to identify the specific metric.

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
            interval = round(duration.total_seconds() / len(timestamps))
            return [i * interval for i in range(len(timestamps))]

        timestamps: list[str] = []
        measurements: list[float] = []
        for stats in statistics:
            if not isinstance(stats, dict):
                continue
            timestamp = str(stats["time"])
            raw_value = stats[f"{section}.{indicator}"]
            if isinstance(raw_value, int | float | str):
                value = float(raw_value)
                timestamps.append(timestamp)
                measurements.append(value)
        return get_durations(timestamps), measurements

    def plot_resource_graph(
        self,
        graph_file: Path,
    ) -> None:
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

        Returns:
            None
        """
        for scenario_name in self.scenario_names:
            fig, ax = pyplot.subplots(2)
            fig.suptitle(f"Resource usage: {scenario_name}")
            fig.set_size_inches(self.px(1920), self.px(1080))
            graph_file_path = graph_file.parent / f"{scenario_name}.{graph_file.name}"
            logger.info('Writing graph "%s"...', graph_file_path)
            for job_name, data in self.jobs.items():
                statistics = data[1].get(scenario_name, [])
                xmax = 60
                for subplot, section, indicator in [
                    [ax[0], "cpu_info", "cpu_percent"],
                    [ax[1], "memory_info", "virtual_memory_percent"],
                ]:
                    if not statistics:
                        # no statistics available
                        continue
                    durations, values = self._plottable_resource_data(
                        statistics, section, indicator
                    )
                    xmax = int(durations[-1]) if durations[-1] > xmax else xmax
                    average = fmean(values or [0])
                    # total_duration = datetime.timedelta(seconds=durations[-1])
                    pg = subplot.plot(
                        durations,
                        values,
                        label=f"{job_name} (avg={round(average, 2)}%)",
                    )
                    subplot.legend()
                    # draw a dashed line for the average in the same color
                    subplot.plot(
                        [durations[0], durations[-1]],
                        [average, average],
                        linestyle="dashed",
                        color=pg[-1].get_color(),
                    )
                    subplot.set(ylabel=indicator, xlabel="time (s)")
                    subplot.set_ylim(ymin=0, ymax=100)
                    subplot.set_xlim(xmin=0, xmax=xmax)
            pyplot.savefig(graph_file_path)
            pyplot.close()

    def read_job_names(self) -> list[str]:
        """
        Retrieves and returns a sorted list of job names that are either present on disk or exist
        in the database.

        The method checks for job directories in the specified root directory and verifies the
        existence of corresponding job files. It also checks the database for job names.
        Only job names that are found on disk or in the database are returned.

        Returns:
            list[str]: A sorted list of valid job names found on disk or in the database.
        """
        if self.root_dir.is_dir():
            print(f'Scanning root dir "{self.root_dir}" for reports...')
            job_names_on_disk = [
                job.name
                for job in self.root_dir.iterdir()
                if job.is_dir() and self.job_file_path(job.name).exists()
            ]
        else:
            print(f'Skipping root dir "{self.root_dir}": Folder not found!')
            job_names_on_disk = []
        return sorted(
            [
                job_name
                for job_name in self.args.job_names
                if job_name in job_names_on_disk
                or (self.read_from_database and self.database.check_job(job_name))
            ]
        )

    def read_job_data(self, job_name: str) -> Measurements:
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
        job_file_path = self.job_file_path(job_name)
        if job_file_path.exists() and self.read_from_filesystem:
            logger.info('Reading data for job "%s" from the filesystem...', job_name)
            data = self.read_json(job_file_path)
            if isinstance(data, dict):
                return data

        benchmarks: list[dict[str, str | Measurements]] = []
        if not (self.read_from_database and self.database.check_job(job_name)):
            return {"benchmarks": benchmarks}
        logger.info('Reading data for job "%s" from the database...', job_name)
        job_details = self.database.get_job(job_name=job_name)
        for scenario_name in self.scenario_names:
            scenario_id, _, scenario_description = self.database.get_scenario(scenario_name)
            test_id = self.database.get_test(job_details.job_id, scenario_id)[0]
            if benchmark_statistics := self.database.read_benchmark_statistics(test_id):
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

    def read_scenario_names(self) -> list[str]:
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
                    if (job_file_path := self.job_file_path(job_name)).exists()
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

    def read_scenario_data(self, job_name: str) -> dict[str, MeasurementsList]:
        """
        Reads measurement data for each scenario associated with a given job name from either the
        filesystem or a database.

        Args:
            job_name (str): The name of the job for which scenario data should be retrieved.

        Returns:
            dict[str, MeasurementsList]: A dictionary mapping scenario names to measurement lists.

        Notes:
            - If `read_from_filesystem` and the scenario file exists, filessystem data is read.
            - If `read_from_database` and the job exists in the database, database data is read.
            - If no data is found for a scenario, an empty list is returned for that scenario.
        """
        scenario_data: dict[str, MeasurementsList] = {}
        for scenario_name in self.scenario_names:
            scenario_file_path = self.scenario_file_path(job_name, scenario_name)
            if scenario_file_path.exists() and self.read_from_filesystem:
                # read measurements from file
                scenario_data[scenario_name] = (
                    data if isinstance(data := self.read_json(scenario_file_path), list) else []
                )
            elif self.read_from_database and self.database.check_job(job_name=job_name):
                # read measurements from database
                if (job_details := self.database.get_job(job_name=job_name)) is None:
                    scenario_data[scenario_name] = []
                    continue
                job_id = job_details[0]
                scenario_id = self.database.get_scenario(scenario_name=scenario_name)[0]
                test_id = self.database.get_test(job_id=job_id, scenario_id=scenario_id)[0]
                scenario_data[scenario_name] = self.database.read_measurements(test_id=test_id)
        return scenario_data

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
                    job_name: (self.read_job_data(job_name), self.read_scenario_data(job_name))
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
            job_file_path = self.job_file_path(job_name)
            if self.write_json_files:
                logger.info('Writing data for job "%s" to the filesystem...', job_name)
                job_file_path.parent.mkdir(parents=True, exist_ok=True)
                with job_file_path.open("w", encoding="utf-8") as json_file:
                    json.dump(benchmark_data, json_file, indent=4, default=str)
            for scenario_name, performance_data in scenario_data.items():
                if self.write_json_files:
                    with self.scenario_file_path(job_name, scenario_name).open(
                        "w", encoding="utf-8"
                    ) as json_file:
                        json.dump(performance_data, json_file, indent=4, default=str)

                if not len(performance_data) > 0:
                    continue

                if self.write_to_database:
                    logger.info('Writing data for job "%s" to the database...', job_name)
                    job_endtime = (
                        Datetime.fromisoformat(str(_ts))
                        if (_ts := benchmark_data.get("end_time", benchmark_data.get("datetime")))
                        else Datetime.now()
                    )
                    job_starttime = (
                        Datetime.fromisoformat(str(_ts))
                        if (_ts := benchmark_data.get("start_time"))
                        else job_endtime
                    )
                    self.database.write_performance_data(
                        job_name=job_name,
                        job_starttime=job_starttime,
                        job_endtime=job_endtime,
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
    def get_mean_value(measurements: MeasurementsList, metric_name: str) -> float:
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

    def calculate_baseline(self, scenario_name: str) -> AverageValues:
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
                logger.error('Scenario "%s" not found in job "%s"!', scenario_name, job_name)
                continue
            time_averages.append(benchmark["stats"]["mean"])
            if scenario_name not in job[1]:
                continue
            if not (measurements := job[1][scenario_name]):
                continue
            cpu_averages.append(self.get_mean_value(measurements, "cpu_info.cpu_percent"))
            mem_averages.append(
                self.get_mean_value(measurements, "memory_info.virtual_memory_percent")
            )
        time_baseline = fmean(time_averages) if time_averages else 0.0
        cpu_baseline = fmean(cpu_averages) if cpu_averages else 0.0
        mem_baseline = fmean(mem_averages) if mem_averages else 0.0

        return AverageValues(*(time_baseline, cpu_baseline, mem_baseline))

    def current_averages(self, scenario_name: str) -> AverageValues | None:
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
        cpu_avg = self.get_mean_value(job[1][scenario_name], "cpu_info.cpu_percent")
        mem_avg = self.get_mean_value(job[1][scenario_name], "memory_info.virtual_memory_percent")

        return AverageValues(*(time_avg, cpu_avg, mem_avg))

    def validate_performance_baselines(self) -> list[str]:
        """
        Validate current performance metrics against calculated baselines for each test scenario.

        For every scenario the method retrieves the current averaged metrics (time, CPU, memory)
        and a computed baseline, then compares them using a fixed overshoot tolerance (+10%).

        An alert is generated when any of the following averaged metrics exceeds its baseline by
        more than the tolerance percentage:
            - Execution time (avg_time)
            - CPU usage (avg_cpu)
            - Memory usage (avg_mem)

        If no current data (averages) are available for a scenario, an alert is added.

        Returns:
            list[str]
                A list of human-readable alert messages. The list is empty if all scenarios
                are within tolerated performance bounds.
        """
        overshoot_tolerance = 10

        alerts = []
        for scenario_name in self.scenario_names:
            msg_prefix = f"Scenario {scenario_name}: "
            msg_suffix = f"; tolerance: +{overshoot_tolerance}%)"
            if scenario_name == "test_performance_piggyback":
                # ignore dcd piggyback test for now
                continue
            if not scenario_name.startswith("test_"):
                continue
            averages = self.current_averages(scenario_name)
            if not averages:
                alerts.append(f"{msg_prefix}Missing data! Test aborted?")
                continue
            baseline = self.calculate_baseline(scenario_name)
            if averages.avg_time > baseline.avg_time * (100 + overshoot_tolerance) / 100:
                overshoot = round((averages.avg_time / baseline.avg_time) * 100 - 100, 2)
                msg = (
                    f"Execution time baseline exceeded by {overshoot}% "
                    f"(baseline: {round(baseline.avg_time, 2)};"
                    f" actual: {round(averages.avg_time, 2)}"
                )

                alerts.append(f"{msg_prefix}{msg}{msg_suffix}")
            if averages.avg_cpu > baseline.avg_cpu * (100 + overshoot_tolerance) / 100:
                overshoot = round((averages.avg_cpu / baseline.avg_cpu) * 100 - 100, 2)
                msg = (
                    f"CPU usage baseline exceeded by {overshoot}% "
                    f"(baseline: {round(baseline.avg_cpu, 2)}%;"
                    f" actual: {round(averages.avg_cpu, 2)}%"
                )
                alerts.append(f"{msg_prefix}{msg} {msg_suffix}")
            if averages.avg_mem > baseline.avg_mem * (100 + overshoot_tolerance) / 100:
                overshoot = round((averages.avg_mem / baseline.avg_mem) * 100 - 100, 2)
                msg = (
                    f"Memory usage baseline exceeded by {overshoot}% "
                    f"(baseline: {round(baseline.avg_mem, 2)}%;"
                    f" actual: {round(averages.avg_mem, 2)}%"
                )
                alerts.append(f"{msg_prefix}{msg}{msg_suffix}")
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

    def job_name() -> Callable:
        pattern = r"[0-9](\.[0-9]){2}-[0-9]{4}(\.[0-9]{2}){2}\.c[cemrs]e"

        def validator(value: str) -> str:
            if not (match := re.search(pattern, value)):
                raise argparse.ArgumentTypeError(
                    f"Value '{value}' does not match pattern: {pattern}"
                )
            return match.group(0)

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
        default=Path(__file__).parent.parent.parent / "results" / "performance",
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
        type=bool,
        default=False,
        help="Specifies to read from the database only and ignore filesystem data"
        " (default: %(default)s).",
    )
    parser.add_argument(
        "--skip-filesystem-writes",
        action=argparse.BooleanOptionalAction,
        dest="skip_filesystem_writes",
        type=bool,
        default=False,
        help="Specifies to update the database only and skip writing to the filesystem"
        " (default: %(default)s).",
    )
    parser.add_argument(
        "--skip-database-reads",
        action=argparse.BooleanOptionalAction,
        dest="skip_database_reads",
        type=bool,
        default=False,
        help="Specifies to read from the filesystem only and ignore database data"
        " (default: %(default)s).",
    )
    parser.add_argument(
        "--skip-database-writes",
        action=argparse.BooleanOptionalAction,
        dest="skip_database_writes",
        type=bool,
        default=False,
        help="Specifies to update the filesystem only and skip writing to the database"
        " (default: %(default)s).",
    )
    parser.add_argument(
        "--skip-graph-generation",
        action=argparse.BooleanOptionalAction,
        dest="skip_graph_generation",
        type=bool,
        default=False,
        help="Specifies to skip the graph generation (default: %(default)s).",
    )
    parser.add_argument(
        "--write-json-files",
        action=argparse.BooleanOptionalAction,
        dest="write_json_files",
        type=bool,
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
        "--validate-baselines",
        action=argparse.BooleanOptionalAction,
        dest="validate_baselines",
        type=bool,
        default=True,
        help="Enable performance baseline validation (default: %(default)s).",
    )
    parser.add_argument(
        "--alert-on-failure",
        action=argparse.BooleanOptionalAction,
        dest="alert_on_failure",
        type=bool,
        default=False,
        help="Enable Jira alerter on baseline validation failure (default: %(default)s).",
    )
    parser.add_argument(
        "--sslrootcert-var",
        dest="sslrootcert_var",
        type=str,
        default="QA_ROOT_CERT",
        help="The name of the root certificate variable (default: %(default)s).",
    )
    parser.add_argument(
        "--sslcert-var",
        dest="sslcert_var",
        type=str,
        default="QA_POSTGRES_CERT",
        help="The name of the Postgres certificate variable (default: %(default)s).",
    )
    parser.add_argument(
        "--sslkey-var",
        dest="sslkey_var",
        type=str,
        default="QA_POSTGRES_KEY",
        help="The name of the Postgres key variable (default: %(default)s).",
    )
    parser.add_argument(
        "--sslmode",
        dest="sslmode",
        type=str,
        default="require",
        help="The SSL mode for the Postgres authentication (default: %(default)s).",
    )
    parser.add_argument(
        "--cert-folder",
        dest="cert_folder",
        type=Path,
        default="/tmp/.postgresql" if getenv("CI") else Path.home() / ".postgresql",
        help="The path to write the certificate files to (default: %(default)s).",
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
        "--log-level",
        dest="log_level",
        type=str,
        default="WARNING",
        help="The log level for the application (default: %(default)s).",
    )
    return parser.parse_args(namespace=PerftestPlotArgs())


def main():
    """
    Runs the CLI application for performance test plotting.

    This function initializes the PerftestPlot application with parsed command-line arguments,
    checks for the presence of benchmark jobs, writes performance data, generates graph files
    if requested, and prints the output directory.

    Raises:
        SystemExit: If no benchmark jobs are provided.
    """
    args = parse_args()
    logger.setLevel(args.log_level)
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

    if app.validate_baselines:
        alerts = app.validate_performance_baselines()
        summary = f"Validate performance test {list(app.jobs.keys())[-1]}"
        description = (f"\n  {'\n  '.join(alerts)}") if alerts else "PASSED!"
        print(f"{summary}: {description}")
        if app.alert_on_failure and alerts:
            app.create_ticket(summary=summary, description=description)

    print(app.output_dir)


if __name__ == "__main__":
    main()

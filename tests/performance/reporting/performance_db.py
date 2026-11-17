#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The performance database: jobs, scenarios, tests, benchmark statistics and resource samples.

The schema is in ``database/initdb_performance.sql``. ``perftest_plot.py`` uploads into it and
reads the history for its graphs and baseline checks from it.
"""

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

import logging
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime as Datetime
from pathlib import Path
from typing import Literal, NamedTuple

import psycopg

logger = logging.getLogger(__name__)

Measurements = Mapping[str, object]
MeasurementsList = list[Measurements]
SslMode = Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]


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
        sslmode: SslMode = "require",
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
    def _cursor(self) -> Iterator[psycopg.cursor.Cursor]:
        """Return an active cursor in a new autocommit connection."""
        with self.connection.cursor() as cursor:
            yield cursor

    def _add_job(
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
            with self._cursor() as cursor:
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
        with self._cursor() as cursor:
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

    def delete_job(self, job_name: str) -> bool:
        """
        Delete job details for a given job name from the database.

        Args:
            job_name (str): The name of the job to delete.

        Returns:
            bool: True if the job was deleted, False if the job was not found.

        Raises:
            ValueError: If no job with the specified name is found in the database.
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM jobs
                WHERE job_name = %s
                """,
                (job_name,),
            )
        return cursor.rowcount > 0

    def job_run_name(self, job_name: str, end_timestamp: Datetime) -> str:
        """Return the job name to store a run under.

        The first run keeps the job name, further runs get the suffix "_2", "_3" and so on.
        A run that is stored already, as one of these jobs ended at the same time, keeps the
        name of that job, so its missing scenarios are added to it.
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT job_name, end_timestamp = %s
                FROM jobs
                WHERE job_name = %s OR job_name LIKE %s
                """,
                (end_timestamp, job_name, f"{job_name}\\_%"),
            )
            runs = cursor.fetchall()
        run_numbers = []
        for run_name, stored in runs:
            if not (match := re.fullmatch(rf"{re.escape(job_name)}(?:_([0-9]+))?", run_name)):
                continue
            if stored:
                return str(run_name)
            run_numbers.append(int(match.group(1) or 1))
        return f"{job_name}_{max(run_numbers) + 1}" if run_numbers else job_name

    def delete_test(self, job_name: str, scenario_name: str) -> None:
        """Delete the test results of one scenario of a job from the database."""
        with self._cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM tests
                USING jobs, scenarios
                WHERE tests.job_id = jobs.job_id
                    AND tests.scenario_id = scenarios.scenario_id
                    AND jobs.job_name = %s
                    AND scenarios.scenario_name = %s
                """,
                (job_name, scenario_name),
            )

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
            print(excp)  # part of the script output, like before the split
            return False

    def _add_scenario(self, scenario_name: str, scenario_description: str | None = None) -> int:
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
        if scenario_details := self.get_scenario(scenario_name=scenario_name):
            return scenario_details[0]
        with self._cursor() as cursor:
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

    def get_scenario(self, scenario_name: str) -> ScenarioDetails | None:
        """
        Retrieves the details of a scenario from the database by its name.

        Args:
            scenario_name (str): The name of the scenario to retrieve.

        Returns:
            ScenarioDetails | None: An object containing the scenario's ID, name and description
                or None if the scenario was not found.
        """
        with self._cursor() as cursor:
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
            logger.log(
                logging.WARNING if scenario_name.startswith("test_") else logging.DEBUG,
                'Failed to retrieve scenario "%s"!',
                scenario_name,
            )
            return None
        return ScenarioDetails(*scenario_details)

    def get_scenario_names(self) -> list[str]:
        """
        Retrieves all unique scenario names from the 'scenarios' table in the database.

        Returns:
            list[str]: A list containing the distinct scenario names.
        """
        with self._cursor() as cursor:
            cursor.execute("""SELECT DISTINCT scenario_name FROM scenarios""")
            return [_[0] for _ in cursor.fetchall()]

    def _add_test(
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
        if test_details := self.get_test(job_id=job_id, scenario_id=scenario_id):
            return test_details[0]
        with self._cursor() as cursor:
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

    def get_test(self, job_id: int, scenario_id: int) -> TestDetails | None:
        """
        Retrieve the details of a specific test from the database based on job and scenario IDs.

        Args:
            job_id (int): The ID of the job associated with the test.
            scenario_id (int): The ID of the scenario associated with the test.

        Returns:
            TestDetails | None: An object containing the details of the test
                or None if the test was not found.
        """
        with self._cursor() as cursor:
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
            return None
        return TestDetails(*test_details)

    def read_benchmark_data(self, test_id: int) -> Measurements:
        """
        Reads benchmark data for a given test from the database.

        Fetches metric names and their measured values associated with the specified test ID,
        ignoring any values that are not of type int or float. The results are returned as a
        dictionary mapping metric names to their float values, sorted by metric name in
        ascending order.

        Args:
            test_id (int): The ID of the benchmark test to retrieve statistics for.

        Returns:
            Measurements: A dict containing metric names and their corresponding float values.

        Note:
            Any value types other than int and float are ignored.
        """
        with self._cursor() as cursor:
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

    def write_benchmark_data(self, test_id: int, benchmark_statistics: Measurements) -> None:
        """
        Writes benchmark data for a given test to the database.

        Args:
            test_id (int): The identifier of the test for which statistics are recorded.
            benchmark_statistics (Measurements): A dictionary containing benchmark metrics and
                their values.

        Note:
            Any value types other than int and float are ignored.
        """
        benchmark_data: dict[str, int | float] = {
            key: val for key, val in benchmark_statistics.items() if isinstance(val, int | float)
        }
        if "data" in benchmark_statistics:
            assert isinstance(benchmark_statistics["data"], list)
            for i, value in enumerate(benchmark_statistics["data"]):
                benchmark_data[f"data{i}"] = value
        with self._cursor() as cursor:
            for metric_name, value in benchmark_data.items():
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

    def read_scenario_data(self, job_name: str, scenario_name: str) -> MeasurementsList:
        """
        Reads measurement data for a given job name and scenario from the database.

        Args:
            job_name (str): The name of the job for which scenario data should be retrieved.
            scenario_name (str): The name of the scenario for which data should be retrieved.

        Returns:
            MeasurementsList: A list with the measurements for the scenario.

        Notes:
            - If no data is found for the scenario, an empty list is returned.
        """
        if (job_details := self.get_job(job_name=job_name)) is None:
            return []
        if (scenario_details := self.get_scenario(scenario_name=scenario_name)) is None:
            return []
        if (
            test_details := self.get_test(job_id=job_details[0], scenario_id=scenario_details[0])
        ) is None:
            return []
        with self._cursor() as cursor:
            cursor.execute(
                """
                    SELECT metric_name, measured_at, measured_value
                    FROM metrics
                    WHERE test_id = %s
                    ORDER BY metric_name ASC, measured_at ASC
                    """,
                (test_details[0],),
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

    def write_scenario_data(
        self,
        job_name: str,
        job_starttime: Datetime,
        job_endtime: Datetime,
        product_release: str,
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
            product_release (str): Product release the job measured.
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
        job_id = self._add_job(
            job_name=job_name,
            start_timestamp=job_starttime,
            end_timestamp=job_endtime,
            product_release=product_release,
            system_name=str(machine_info.get("system", "")),
            system_release=str(machine_info.get("release", "")),
            system_machine=str(machine_info.get("machine", "")),
            host_name=str(machine_info.get("node", "")),
        )
        scenario_id = self._add_scenario(scenario_name)
        if not self.get_test(job_id=job_id, scenario_id=scenario_id):
            test_id = self._add_test(
                job_id=job_id,
                scenario_id=scenario_id,
                start_timestamp=test_starttime,
                end_timestamp=test_endtime,
            )
            with self._cursor() as cursor:
                data = []
                for measurement in performance_data:
                    assert isinstance(measurement, dict)
                    for metric_name in measurement:
                        if metric_name == "time":
                            continue
                        data.append(
                            (test_id, metric_name, measurement[metric_name], measurement["time"])
                        )
                cursor.executemany(
                    """
                    INSERT INTO metrics (test_id, metric_name, measured_value, measured_at)
                    VALUES (%s,%s,%s,%s)
                    """,
                    data,
                )

            assert isinstance(benchmarks := benchmark_data["benchmarks"], list)
            benchmark_statistics: Measurements | None = next(
                (_["stats"] for _ in benchmarks if _["name"] == scenario_name), None
            )
            if benchmark_statistics:
                self.write_benchmark_data(
                    test_id=test_id,
                    benchmark_statistics=benchmark_statistics,
                )

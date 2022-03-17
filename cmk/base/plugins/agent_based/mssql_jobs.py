#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from typing import Any, Final, Mapping, NamedTuple, Optional

from .agent_based_api.v1 import check_levels, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

# Sample output:

# <<<mssql_jobs:sep(09)>>>
# MSSQLSERVER	{E86617B1-A9B2-4443-8916-312AB1F526DE}	syspolicy_purge_history	1	20200821	20000	5		0	0	0	1	2020-08-21 07:54:34

# Sample error:
# MSSQLSERVER ERROR: Incorrect syntax near the keyword 'LEFT'. (SQLState: 42000/NativeError: 156). Incorrect syntax near 'sjh'. (SQLState: 42000/NativeError: 102).

# Database documentation:
# https://docs.microsoft.com/en-us/sql/relational-databases/system-tables/dbo-sysjobs-transact-sql?view=sql-server-ver15


class JobSpec(NamedTuple):
    last_run_duration: Optional[float]
    last_run_outcome: str
    last_run_datetime: str
    enabled: bool
    schedule_enabled: bool
    next_run_datetime: str
    last_outcome_message: str
    state: State


_DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


_COL_HEADERS: Final = (
    "job_id",
    "job_name",
    "job_enabled",
    "next_run_date",
    "next_run_time",
    "last_run_outcome",
    "last_outcome_message",
    "last_run_date",
    "last_run_time",
    "last_run_duration",
    "schedule_enabled",
    "server_current_time",
)

_OUTCOME_TRANSLATION: Final = {
    "": "N/A",
    "0": "Fail",
    "1": "Succeed",
    "2": "Retry",
    "3": "Cancel",
    "4": "In progress",
    "5": "Unknown",
}

_STATUS_MAPPING: Final = {
    "Fail": State.CRIT,
    "Succeed": State.OK,
    "Retry": State.OK,
    "Cancel": State.OK,
    "In progress": State.OK,
    "Unknown": State.UNKNOWN,
}


def _calculate_seconds(raw_duration: str) -> Optional[float]:
    """Return the number of seconds from a string in HHMMSS format.
    The strings are of variable length, e.g. 124 = 1 minute 24 seconds.

    >>> _calculate_seconds('0')
    0.0

    >>> _calculate_seconds('3')
    3.0

    >>> _calculate_seconds('124')
    84.0

    >>> _calculate_seconds('12314')
    4994.0

    """

    if not (length := len(raw_duration)):
        return None

    if length <= 2:
        return float(raw_duration)

    if length <= 4:
        raw_seconds = float(raw_duration[-2:])
        raw_minutes = float(raw_duration[:-2])
        return raw_seconds + raw_minutes * 60

    raw_seconds = float(raw_duration[-2:])
    raw_minutes = float(raw_duration[-4:-2])
    raw_hours = float(raw_duration[:-4])

    return raw_seconds + raw_minutes * 60 + raw_hours * 3600


def _format_to_datetime(raw_date: str, raw_time: str) -> str:
    """Return a valid datetime from date and time strings in YYYYMMDD and HHMMSS formats respectively.
    The date and/or time may be set to '0'. The time may be of variable length, e.g. 300 = 00:03:00.

    >>> _format_to_datetime('20200821', '132400')
    '2020-08-21 13:24:00'

    >>> _format_to_datetime('20200821', '300')
    '2020-08-21 00:03:00'

    >>> _format_to_datetime('20200821', '0')
    '2020-08-21 00:00:00'

    >>> _format_to_datetime('0', '0')
    'N/A'

    """
    if raw_date in ["0", ""]:
        return "N/A"

    source_datetime = datetime.datetime.strptime(
        raw_date + " " + raw_time.zfill(6),
        "%Y%m%d %H%M%S",
    )

    return datetime.datetime.strftime(source_datetime, _DATETIME_FMT)


def parse_mssql_jobs(string_table: StringTable) -> Mapping[str, JobSpec]:

    section = {}
    for line in string_table:
        if len(line) == 1:
            continue
        # The output may contain more than one line per job, depending on how often it is scheduled.
        # The user is only interested in the upcoming "next_run_time".
        if line[1] in section:
            continue

        job = dict(zip(_COL_HEADERS, line))

        last_run_outcome = _OUTCOME_TRANSLATION[job["last_run_outcome"]]

        section[job["job_name"]] = JobSpec(
            last_run_duration=_calculate_seconds(job["last_run_duration"]),
            last_run_outcome=last_run_outcome,
            last_run_datetime=_format_to_datetime(
                job["last_run_date"],
                job["last_run_time"],
            ),
            enabled=job["job_enabled"] not in ("", "0"),
            schedule_enabled=job["schedule_enabled"] not in ("", "0"),
            next_run_datetime=_format_to_datetime(
                job["next_run_date"],
                job["next_run_time"],
            ),
            last_outcome_message=job["last_outcome_message"],
            state=_STATUS_MAPPING.get(last_run_outcome, State.UNKNOWN),
        )

    return section


def discover_mssql_jobs(section: Mapping[str, JobSpec]) -> DiscoveryResult:
    for job_name in section:
        yield Service(item=job_name)


def check_mssql_jobs(
    item: str, params: Mapping[str, Any], section: Mapping[str, JobSpec]
) -> CheckResult:

    if (job_specs := section.get(item)) is None:
        return State(params["status_missing_jobs"]), "Job not found"

    if job_specs.last_run_duration is not None:
        yield from check_levels(
            value=job_specs.last_run_duration,
            metric_name="database_job_duration",
            levels_upper=params["run_duration"],
            render_func=render.timespan,
            label="Last duration",
        )

    yield Result(
        state=State.OK if params["ignore_db_status"] else job_specs.state,
        summary=f"MSSQL status: {job_specs.last_run_outcome}",
    )

    yield Result(state=State.OK, summary=f"Last run: {job_specs.last_run_datetime}")

    status_disabled_jobs = State(params["status_disabled_jobs"])
    if not job_specs.enabled:
        yield Result(state=status_disabled_jobs, summary="Job is disabled")
    elif not job_specs.schedule_enabled:
        yield Result(state=status_disabled_jobs, summary="Schedule is disabled")
    else:
        yield Result(state=State.OK, summary=f"Next run: {job_specs.next_run_datetime}")

    yield Result(state=State.OK, notice=f"Outcome message: {job_specs.last_outcome_message}")


register.agent_section(
    name="mssql_jobs",
    parse_function=parse_mssql_jobs,
)

register.check_plugin(
    name="mssql_jobs",
    discovery_function=discover_mssql_jobs,
    check_function=check_mssql_jobs,
    service_name="MSSQL Job: %s",
    check_ruleset_name="mssql_jobs",
    check_default_parameters={
        "ignore_db_status": True,
        "status_disabled_jobs": 0,
        "status_missing_jobs": 2,
        "run_duration": None,
    },
)

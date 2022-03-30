#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from copy import copy
from typing import List, Union

import pytest

from tests.testlib import on_time

from cmk.base.plugins.agent_based import job
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State

SECTION_1: job.Section = {
    "SHREK": {
        "running": False,
        "start_time": 1547301201,
        "exit_code": 0,
        "metrics": {
            "real_time": 120.0,
            "user_time": 1.0,
            "system_time": 0.0,
            "reads": 0,
            "writes": 0,
            "max_res_bytes": 1234000,
            "avg_mem_bytes": 1000,
            "invol_context_switches": 12,
            "vol_context_switches": 23,
        },
    },
    "SNOWWHITE": {
        "running": False,
        "start_time": 1557301201,
        "exit_code": 1,
        "running_start_time": [
            1557301261,
            1557301321,
            1557301381,
            1557301441,
            1537301501,
            1557301561,
        ],
        "metrics": {
            "real_time": 360.0,
            "user_time": 0.0,
            "system_time": 0.0,
            "reads": 0,
            "writes": 0,
            "max_res_bytes": 2224000,
            "avg_mem_bytes": 0,
            "invol_context_switches": 1,
            "vol_context_switches": 2,
        },
    },
}

SECTION_2: job.Section = {
    "backup.sh": {
        "running": False,
        "start_time": 1415204091,
        "exit_code": 0,
        "running_start_time": [1415205713],
        "metrics": {
            "real_time": 281.65,
            "user_time": 277.7,
            "system_time": 32.12,
            "reads": 0,
            "writes": 251792,
            "max_res_bytes": 130304000,
            "avg_mem_bytes": 0,
            "invol_context_switches": 16806,
            "vol_context_switches": 32779,
        },
    },
    "cleanup_remote_logs": {
        "running": False,
        "start_time": 1415153430,
        "exit_code": 0,
        "metrics": {
            "real_time": 9.9,
            "user_time": 8.85,
            "system_time": 0.97,
            "reads": 96,
            "writes": 42016,
            "max_res_bytes": 11456000,
            "avg_mem_bytes": 0,
            "invol_context_switches": 15,
            "vol_context_switches": 274,
        },
    },
}

SECTION_3: job.Section = {
    "process1minrtu": {
        "running": False,
        "start_time": 1560925321,
        "exit_code": 0,
        "metrics": {
            "real_time": 2.63,
            "user_time": 0.62,
            "system_time": 0.31,
            "reads": 90736,
            "writes": 0,
            "max_res_bytes": 109380000,
            "avg_mem_bytes": 0,
            "invol_context_switches": 203407,
            "vol_context_switches": 2025,
        },
    },
}

TIME = 1594300620.0, "CET"


def _modify_start_time(
    j: job.Job,
    start_time: Union[float, List[int]],
) -> job.Job:
    new_job: job.Job = copy(j)
    if isinstance(start_time, list):
        new_job["running_start_time"] = start_time
    else:
        new_job["start_time"] = start_time
    return new_job


@pytest.mark.parametrize(
    "timestr,expected_result",
    [
        ("0:00.00", 0.0),
        ("1:02.00", 62.0),
        ("35:30:2.12", 35 * 60**2 + 30 * 60 + 2.12),
    ],
)
def test_job_parse_real_time(timestr, expected_result):
    assert job._job_parse_real_time(timestr) == expected_result


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        (
            [
                ["==>", "SHREK", "<=="],
                ["start_time", "1547301201"],
                ["exit_code", "0"],
                ["real_time", "2:00.00"],
                ["user_time", "1.00"],
                ["system_time", "0.00"],
                ["reads", "0"],
                ["writes", "0"],
                ["max_res_kbytes", "1234"],
                ["avg_mem_kbytes", "1"],
                ["invol_context_switches", "12"],
                ["vol_context_switches", "23"],
                ["==>", "SNOWWHITE", "<=="],
                ["start_time", "1557301201"],
                ["exit_code", "1"],
                ["real_time", "6:00.00"],
                ["user_time", "0.00"],
                ["system_time", "0.00"],
                ["reads", "0"],
                ["writes", "0"],
                ["max_res_kbytes", "2224"],
                ["avg_mem_kbytes", "0"],
                ["invol_context_switches", "1"],
                ["vol_context_switches", "2"],
                ["==>", "SNOWWHITE.27997running", "<=="],
                ["start_time", "1557301261"],
                ["==>", "SNOWWHITE.28912running", "<=="],
                ["start_time", "1557301321"],
                ["==>", "SNOWWHITE.29381running", "<=="],
                ["start_time", "1557301381"],
                ["==>", "SNOWWHITE.30094running", "<=="],
                ["start_time", "1557301441"],
                ["==>", "SNOWWHITE.30747running", "<=="],
                ["start_time", "1537301501"],
                ["==>", "SNOWWHITE.31440running", "<=="],
                ["start_time", "1557301561"],
            ],
            SECTION_1,
        ),
        (
            [
                ["==>", "backup.sh", "<=="],
                ["start_time", "1415204091"],
                ["exit_code", "0"],
                ["real_time", "4:41.65"],
                ["user_time", "277.70"],
                ["system_time", "32.12"],
                ["reads", "0"],
                ["writes", "251792"],
                ["max_res_kbytes", "130304"],
                ["avg_mem_kbytes", "0"],
                ["invol_context_switches", "16806"],
                ["vol_context_switches", "32779"],
                ["==>", "backup.sh.running", "<=="],
                ["start_time", "1415205713"],
                ["==>", "cleanup_remote_logs", "<=="],
                ["start_time", "1415153430"],
                ["exit_code", "0"],
                ["real_time", "0:09.90"],
                ["user_time", "8.85"],
                ["system_time", "0.97"],
                ["reads", "96"],
                ["writes", "42016"],
                ["max_res_kbytes", "11456"],
                ["avg_mem_kbytes", "0"],
                ["invol_context_switches", "15"],
                ["vol_context_switches", "274"],
            ],
            SECTION_2,
        ),
        (
            [
                ["==>", "process1minrtu", "<=="],
                ["start_time", "1560925321"],
                ["exit_code", "0"],
                ["real_time", "0:02.63"],
                ["user_time", "0.62"],
                ["system_time", "0.31"],
                ["reads", "90736"],
                ["writes", "0"],
                ["max_res_kbytes", "109380"],
                ["avg_mem_kbytes", "0"],
                ["invol_context_switches", "203407"],
                ["vol_context_switches", "2025"],
                ["==>", "process1minrtu.30166running", "<=="],
                ["start_time", "1560921361"],
                ["Command", "terminated", "by", "signal", "9"],
                ["exit_code", "0"],
                ["real_time", "1:32:44"],
                ["user_time", "2249.08"],
                ["system_time", "334.76"],
                ["reads", "34325712"],
                ["writes", "256"],
                ["max_res_kbytes", "7404976"],
                ["avg_mem_kbytes", "0"],
                ["invol_context_switches", "510568"],
                ["vol_context_switches", "1344324"],
            ],
            SECTION_3,
        ),
        (
            # I am not sure how that happened, but we have seen empty files
            [
                [
                    "==>",
                    "empty_file.123running",
                    "<==",
                ]
            ],
            {},
        ),
    ],
)
def test_parse(string_table, expected_parsed_data):
    assert job.parse_job(string_table) == expected_parsed_data


RESULTS_SHREK: List[Union[Metric, Result]] = [
    Result(state=State.OK, summary="Latest exit code: 0"),
    Result(state=State.OK, summary="Real time: 2 minutes 0 seconds"),
    Metric("real_time", 120.0, boundaries=(0.0, None)),
    Result(state=State.OK, notice="Latest job started at Jan 12 2019 14:53:21"),
    Metric("start_time", 1547301201.0),
    Result(state=State.OK, summary="Job age: 1 year 178 days"),
    Result(state=State.OK, notice="Avg. memory: 1000 B"),
    Metric("avg_mem_bytes", 1000.0, boundaries=(0.0, None)),
    Result(state=State.OK, notice="Invol. context switches: 12"),
    Metric("invol_context_switches", 12.0, boundaries=(0.0, None)),
    Result(state=State.OK, notice="Max. memory: 1.18 MiB"),
    Metric("max_res_bytes", 1234000.0, boundaries=(0.0, None)),
    Result(state=State.OK, notice="Filesystem reads: 0"),
    Metric("reads", 0.0, boundaries=(0.0, None)),
    Result(state=State.OK, notice="System time: 0 seconds"),
    Metric("system_time", 0.0, boundaries=(0.0, None)),
    Result(state=State.OK, notice="User time: 1 second"),
    Metric("user_time", 1.0, boundaries=(0.0, None)),
    Result(state=State.OK, notice="Vol. context switches: 23"),
    Metric("vol_context_switches", 23.0, boundaries=(0.0, None)),
    Result(state=State.OK, notice="Filesystem writes: 0"),
    Metric("writes", 0.0, boundaries=(0.0, None)),
]


@pytest.mark.parametrize(
    "job_data, age_levels, exit_code_to_state_map, expected_results",
    [
        (
            SECTION_1["SHREK"],
            (0, 0),
            {0: State.OK},
            RESULTS_SHREK,
        ),
        (
            SECTION_1["SHREK"],
            (1, 2),
            {0: State.OK},
            [
                *RESULTS_SHREK[0:5],
                Result(
                    state=State.CRIT,
                    summary="Job age: 1 year 178 days (warn/crit at 1 second/2 seconds)",
                ),
                *RESULTS_SHREK[6:],
            ],
        ),
        (
            SECTION_1["SHREK"],
            (0, 0),
            {0: State.WARN},
            [
                Result(
                    state=State.WARN,
                    summary="Latest exit code: 0",
                ),
                *RESULTS_SHREK[1:],
            ],
        ),
        (
            _modify_start_time(
                SECTION_1["SHREK"],
                [1557301261, 1557301321, 1557301381, 1557301441, 1537301501, 1557301561],
            ),
            (1, 2),
            {0: State.OK},
            [
                *RESULTS_SHREK[:3],
                Result(
                    state=State.OK,
                    notice=(
                        "6 jobs are currently running, started at"
                        " May 08 2019 09:41:01, May 08 2019 09:42:01,"
                        " May 08 2019 09:43:01, May 08 2019 09:44:01,"
                        " Sep 18 2018 22:11:41, May 08 2019 09:46:01"
                    ),
                ),
                Result(
                    state=State.CRIT,
                    summary=(
                        "Job age (currently running): "
                        "1 year 63 days (warn/crit at 1 second/2 seconds)"
                    ),
                ),
                *RESULTS_SHREK[6:],
            ],
        ),
    ],
)
def test_process_job_stats(
    job_data,
    age_levels,
    exit_code_to_state_map,
    expected_results,
):
    with on_time(*TIME):
        assert list(
            job._process_job_stats(
                job_data,
                age_levels,
                exit_code_to_state_map,
                time.time(),
            )
        ) == list(expected_results)


@pytest.mark.parametrize(
    "item, params, section, expected_results",
    [
        (
            "SHREK",
            {"age": (0, 0)},
            SECTION_1,
            RESULTS_SHREK,
        ),
        (
            "item",
            {"age": (0, 0)},
            {"item": {}},
            [Result(state=State.UNKNOWN, summary="Got incomplete information for this job")],
        ),
        (
            "cleanup_remote_logs",
            {"age": (0, 0)},
            SECTION_2,
            [
                Result(
                    state=State.OK, summary="Latest exit code: 0", details="Latest exit code: 0"
                ),
                Result(state=State.OK, summary="Real time: 10 seconds"),
                Metric("real_time", 9.9, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Latest job started at Nov 05 2014 03:10:30"),
                Metric("start_time", 1415153430.0),
                Result(state=State.OK, summary="Job age: 5 years 248 days"),
                Result(state=State.OK, notice="Avg. memory: 0 B"),
                Metric("avg_mem_bytes", 0.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Invol. context switches: 15"),
                Metric("invol_context_switches", 15.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Max. memory: 10.9 MiB"),
                Metric("max_res_bytes", 11456000.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Filesystem reads: 96"),
                Metric("reads", 96.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="System time: 970 milliseconds"),
                Metric("system_time", 0.97, boundaries=(0.0, None)),
                Result(state=State.OK, notice="User time: 9 seconds"),
                Metric("user_time", 8.85, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Vol. context switches: 274"),
                Metric("vol_context_switches", 274.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Filesystem writes: 42016"),
                Metric("writes", 42016.0, boundaries=(0.0, None)),
            ],
        ),
        (
            "backup.sh",
            {"age": (1, 2)},
            SECTION_2,
            [
                Result(state=State.OK, summary="Latest exit code: 0"),
                Result(state=State.OK, summary="Real time: 4 minutes 42 seconds"),
                Metric("real_time", 281.65, boundaries=(0.0, None)),
                Result(
                    state=State.OK,
                    notice="1 job is currently running, started at Nov 05 2014 17:41:53",
                ),
                Result(
                    state=State.CRIT,
                    summary="Job age (currently running): 5 years 247 days (warn/crit at 1 second/2 seconds)",
                ),
                Result(state=State.OK, notice="Avg. memory: 0 B"),
                Metric("avg_mem_bytes", 0.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Invol. context switches: 16806"),
                Metric("invol_context_switches", 16806.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Max. memory: 124 MiB"),
                Metric("max_res_bytes", 130304000.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Filesystem reads: 0"),
                Metric("reads", 0.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="System time: 32 seconds"),
                Metric("system_time", 32.12, boundaries=(0.0, None)),
                Result(state=State.OK, notice="User time: 4 minutes 38 seconds"),
                Metric("user_time", 277.7, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Vol. context switches: 32779"),
                Metric("vol_context_switches", 32779.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Filesystem writes: 251792"),
                Metric("writes", 251792.0, boundaries=(0.0, None)),
            ],
        ),
        (
            "missing",
            {"age": (1, 2)},
            SECTION_2,
            [],
        ),
    ],
)
def test_check_job(item, params, section, expected_results):
    with on_time(*TIME):
        assert list(job.check_job(item, params, section)) == expected_results

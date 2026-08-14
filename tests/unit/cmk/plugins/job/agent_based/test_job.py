#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

import datetime
from collections.abc import Sequence
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.job.agent_based import job

STRING_TABLE_1: StringTable = [
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
]

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
        "running": True,
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

STRING_TABLE_1_RUNNING = [
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
    ["==>", "SHREK.27997running", "<=="],
    ["start_time", "1557301261"],
    ["==>", "SHREK.28912running", "<=="],
    ["start_time", "1557301321"],
    ["==>", "SHREK.29381running", "<=="],
    ["start_time", "1557301381"],
    ["==>", "SHREK.30094running", "<=="],
    ["start_time", "1557301441"],
    ["==>", "SHREK.30747running", "<=="],
    ["start_time", "1537301501"],
    ["==>", "SHREK.31440running", "<=="],
    ["start_time", "1557301561"],
]

STRING_TABLE_2: StringTable = [
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
]

SECTION_2: job.Section = {
    "backup.sh": {
        "running": True,
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

STRING_TABLE_3: StringTable = [
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
]

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

STRING_TABLE_RUNNING = [
    ["==>", "230-testing-funning.113660running", "<=="],
    ["start_time", "1730709681"],
]

STRING_TABLE_RUNNING_FINISHED_PART = [
    # be careful with the name here: if it ends with "running" everything is broken!
    ["==>", "230-testing-funning", "<=="],
    ["start_time", "1730702588"],
    ["real", "0:02.00"],
    ["user", "0.00"],
    ["sys", "0.00"],
    ["reads", "0"],
    ["writes", "0"],
    ["max_res_kbytes", "2304"],
    ["avg_mem_kbytes", "0"],
    ["invol_context_switches", "0"],
    ["vol_context_switches", "2"],
    ["exit_code", "0"],
]


TIME = 1594300620.0


def test_split_job_tables() -> None:
    assert list(job._split_job_tables(STRING_TABLE_1[:14])) == [
        (["==>", "SHREK", "<=="], STRING_TABLE_1[1:12]),
        (["==>", "SNOWWHITE", "<=="], STRING_TABLE_1[13:14]),
    ]


def test_split_job_tables_yields_empty_bodies() -> None:
    # mk-job creates the file before it has anything to write into it, so the
    # agent can pick it up while it is still empty.
    assert list(job._split_job_tables([["==>", "a", "<=="], ["==>", "b", "<=="]])) == [
        (["==>", "a", "<=="], []),
        (["==>", "b", "<=="], []),
    ]


def test_split_job_tables_drops_lines_before_the_first_header() -> None:
    assert list(job._split_job_tables([["junk"], ["==>", "a", "<=="], ["start_time", "1"]])) == [
        (["==>", "a", "<=="], [["start_time", "1"]]),
    ]


@pytest.mark.parametrize(
    ["body", "expected_result"],
    [
        pytest.param([["start_time", "1547301201"]], False, id="a real running job"),
        pytest.param([], True, id="empty file"),
        pytest.param([["exit_code", "0"]], True, id="no start time"),
        pytest.param(
            [["start_time", "1547301201"], ["exit_code", "137"]],
            True,
            id="killed job, completion data written to the running file",
        ),
    ],
)
def test_is_zombie(body: StringTable, expected_result: bool) -> None:
    assert job._is_zombie(body) is expected_result


@pytest.mark.parametrize(
    "timestr,expected_result",
    [
        ("0:00.00", 0.0),
        ("1:02.00", 62.0),
        ("35:30:2.12", 35 * 60**2 + 30 * 60 + 2.12),
    ],
)
def test_job_parse_real_time(timestr: str, expected_result: float) -> None:
    assert job._job_parse_real_time(timestr) == expected_result


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        pytest.param(
            STRING_TABLE_1,
            SECTION_1,
            id="",
        ),
        pytest.param(
            STRING_TABLE_2,
            SECTION_2,
            id="",
        ),
        pytest.param(
            STRING_TABLE_3,
            SECTION_3,
            id="",
        ),
        pytest.param(
            # Same as SECTION_3, but with the leftover file being the newer one.
            # Its data must not replace the data of the completed job.
            [
                ["==>", "killed_job", "<=="],
                ["start_time", "1560925321"],
                ["exit_code", "0"],
                ["real", "0:02.63"],
                ["==>", "killed_job.30166running", "<=="],
                ["start_time", "1560929999"],
                ["Command", "terminated", "by", "signal", "9"],
                ["exit_code", "0"],
                ["real", "1:32:44"],
            ],
            {
                "killed_job": {
                    "running": False,
                    "start_time": 1560925321,
                    "exit_code": 0,
                    "metrics": {"real_time": 2.63},
                }
            },
            id="leftover running file newer than the completed job",
        ),
        pytest.param(
            [
                ["==>", "killed_job.30166running", "<=="],
                ["start_time", "1560929999"],
                ["Command", "terminated", "by", "signal", "9"],
                ["exit_code", "0"],
                ["real", "1:32:44"],
            ],
            {},
            id="leftover running file without a completed job",
        ),
        pytest.param(
            [
                [
                    "==>",
                    "empty_file.123running",
                    "<==",
                ]
            ],
            {},
            id="empty file",
        ),
        pytest.param(
            [
                [
                    "==>",
                    "bla",
                    "<==",
                ],
                ["real", "1:32:44"],
                ["user", "2249.08"],
                ["sys", "334.76"],
            ],
            {
                "bla": {
                    "running": False,
                    "metrics": {"real_time": 5564.0, "user_time": 2249.08, "system_time": 334.76},
                }
            },
            id="unformatted /usr/bin/time output",
        ),
        pytest.param(
            [
                [
                    "==>",
                    "bla",
                    "<==",
                ],
                ["user", "2249,08"],
            ],
            {
                "bla": {
                    "metrics": {"user_time": 2249.08},
                    "running": False,
                }
            },
            id="localised float (comma instead of dot as decimal marker)",
        ),
        pytest.param(
            [
                ["==>", "IBM", "AIX", "7.3", "Weird", "Time", "Labels", "<=="],
                ["start_time", "1776568200"],
                ["Real", "1.28"],
                ["User", "0.48"],
                ["System", "0.02"],
                ["exit_code", "0"],
            ],
            {
                "IBM AIX 7.3 Weird Time Labels": {
                    "running": False,
                    "start_time": 1776568200,
                    "exit_code": 0,
                    "metrics": {
                        "real_time": 1.28,
                        "user_time": 0.48,
                        "system_time": 0.02,
                    },
                }
            },
            id="AIX time output with capitalized labels",
        ),
        pytest.param(
            # mk-job versions that determine the timestamp via perl write a bare
            # "start_time " if perl is not installed. The parser only evaluates
            # lines consisting of two fields, so the timestamp is dropped.
            [
                ["==>", "Cleanup-Cache-Files", "<=="],
                ["start_time"],
                ["real", "0:00.96"],
                ["user", "0.11"],
                ["sys", "0.50"],
                ["reads", "4608"],
                ["writes", "24"],
                ["max_res_kbytes", "25216"],
                ["avg_mem_kbytes", "0"],
                ["invol_context_switches", "940"],
                ["vol_context_switches", "99"],
                ["exit_code", "0"],
            ],
            {
                "Cleanup-Cache-Files": {
                    "running": False,
                    "exit_code": 0,
                    "metrics": {
                        "real_time": 0.96,
                        "user_time": 0.11,
                        "system_time": 0.5,
                        "reads": 4608,
                        "writes": 24,
                        "max_res_bytes": 25216000,
                        "avg_mem_bytes": 0,
                        "invol_context_switches": 940,
                        "vol_context_switches": 99,
                    },
                }
            },
            id="start_time without a value",
        ),
    ],
)
def test_parse(string_table: StringTable, expected_parsed_data: job.Section) -> None:
    assert job.parse_job(string_table) == expected_parsed_data


# The metrics of SECTION_1["SHREK"], in the order check_job emits them.
_SHREK_METRIC_RESULTS_1 = [
    Result(state=State.OK, summary="Real time: 2 minutes 0 seconds"),
    Metric("real_time", 120.0, boundaries=(0.0, None)),
]
_SHREK_METRIC_RESULTS_2 = [
    Result(state=State.OK, notice="User time: 1 second"),
    Metric("user_time", 1.0, boundaries=(0.0, None)),
    Result(state=State.OK, notice="System time: 0 seconds"),
    Metric("system_time", 0.0, boundaries=(0.0, None)),
    Result(state=State.OK, notice="Filesystem reads: 0"),
    Metric("reads", 0.0, boundaries=(0.0, None)),
    Result(state=State.OK, notice="Filesystem writes: 0"),
    Metric("writes", 0.0, boundaries=(0.0, None)),
    Result(state=State.OK, notice="Max. memory: 1.18 MiB"),
    Metric("max_res_bytes", 1234000.0, boundaries=(0.0, None)),
    Result(state=State.OK, notice="Avg. memory: 1000 B"),
    Metric("avg_mem_bytes", 1000.0, boundaries=(0.0, None)),
    Result(state=State.OK, notice="Invol. context switches: 12"),
    Metric("invol_context_switches", 12.0, boundaries=(0.0, None)),
    Result(state=State.OK, notice="Vol. context switches: 23"),
    Metric("vol_context_switches", 23.0, boundaries=(0.0, None)),
]


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        pytest.param(
            "SHREK",
            # which is what check_plugin_job.check_default_parameters holds
            {"age": (0, 0), "exit_code_to_state_map": [(0, 0)]},
            STRING_TABLE_1,
            [
                Result(state=State.OK, summary="Latest exit code: 0"),
                *_SHREK_METRIC_RESULTS_1,
                Result(state=State.OK, notice="Latest job started at 2019-01-12 14:53:21"),
                Result(state=State.OK, summary="Job age: 1 year 178 days"),
                Metric("job_age", 46999419.0, boundaries=(0.0, None)),
                *_SHREK_METRIC_RESULTS_2,
            ],
            id="no age levels configured",
        ),
        pytest.param(
            "item",
            {"age": (0, 0), "exit_code_to_state_map": [(0, 0)]},
            [["==>", "item", "<=="]],
            [Result(state=State.UNKNOWN, summary="Got incomplete information for this job")],
            id="item present but without any job data",
        ),
        pytest.param(
            "cleanup_remote_logs",
            {"age": (0, 0), "exit_code_to_state_map": [(0, 0)]},
            STRING_TABLE_2,
            [
                Result(state=State.OK, summary="Latest exit code: 0"),
                Result(state=State.OK, summary="Real time: 10 seconds"),
                Metric("real_time", 9.9, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Latest job started at 2014-11-05 03:10:30"),
                Result(state=State.OK, summary="Job age: 5 years 248 days"),
                Metric("job_age", 179147190.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="User time: 9 seconds"),
                Metric("user_time", 8.85, boundaries=(0.0, None)),
                Result(state=State.OK, notice="System time: 970 milliseconds"),
                Metric("system_time", 0.97, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Filesystem reads: 96"),
                Metric("reads", 96.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Filesystem writes: 42016"),
                Metric("writes", 42016.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Max. memory: 10.9 MiB"),
                Metric("max_res_bytes", 11456000.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Avg. memory: 0 B"),
                Metric("avg_mem_bytes", 0.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Invol. context switches: 15"),
                Metric("invol_context_switches", 15.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Vol. context switches: 274"),
                Metric("vol_context_switches", 274.0, boundaries=(0.0, None)),
            ],
            id="completed job with all metrics",
        ),
        pytest.param(
            "backup.sh",
            {"age": (1, 2), "exit_code_to_state_map": [(0, 0)]},
            STRING_TABLE_2,
            [
                Result(state=State.OK, summary="Latest exit code: 0"),
                Result(state=State.OK, summary="Real time: 4 minutes 42 seconds"),
                Metric("real_time", 281.65, boundaries=(0.0, None)),
                Result(
                    state=State.OK,
                    notice="1 job is currently running, started at 2014-11-05 17:41:53",
                ),
                Result(
                    state=State.CRIT,
                    summary="Job age (currently running): 5 years 247 days (warn/crit at 1 second/2 seconds)",
                ),
                Metric("job_age", 179094907.0, levels=(1.0, 2.0), boundaries=(0.0, None)),
                Result(state=State.OK, notice="User time: 4 minutes 38 seconds"),
                Metric("user_time", 277.7, boundaries=(0.0, None)),
                Result(state=State.OK, notice="System time: 32 seconds"),
                Metric("system_time", 32.12, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Filesystem reads: 0"),
                Metric("reads", 0.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Filesystem writes: 251792"),
                Metric("writes", 251792.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Max. memory: 124 MiB"),
                Metric("max_res_bytes", 130304000.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Avg. memory: 0 B"),
                Metric("avg_mem_bytes", 0.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Invol. context switches: 16806"),
                Metric("invol_context_switches", 16806.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Vol. context switches: 32779"),
                Metric("vol_context_switches", 32779.0, boundaries=(0.0, None)),
            ],
            id="age levels breached while one job is running",
        ),
        pytest.param(
            "missing",
            {"age": (1, 2), "exit_code_to_state_map": [(0, 0)]},
            STRING_TABLE_2,
            [],
            id="item not in section",
        ),
        pytest.param(
            "Cleanup-Cache-Files",
            {"age": (0, 0), "exit_code_to_state_map": [(0, 0)]},
            [
                ["==>", "Cleanup-Cache-Files", "<=="],
                ["real_time", "0.96"],
                ["exit_code", "0"],
            ],
            [Result(state=State.UNKNOWN, summary="Got incomplete information for this job")],
            id="job without a start time",
        ),
        pytest.param(
            "Cleanup-Cache-Files",
            {"age": (0, 0), "exit_code_to_state_map": [(0, 0)]},
            [
                ["==>", "Cleanup-Cache-Files", "<=="],
                ["exit_code", "0"],
                ["==>", "Cleanup-Cache-Files.running", "<=="],
                ["start_time", str(int(TIME) - 60)],
            ],
            [
                Result(state=State.OK, summary="Latest exit code: 0"),
                Result(
                    state=State.OK,
                    notice="1 job is currently running, started at 2020-07-09 15:16:00",
                ),
                Result(state=State.OK, summary="Job age (currently running): 1 minute 0 seconds"),
                Metric("job_age", 60.0, boundaries=(0.0, None)),
            ],
            id="running job",
        ),
        pytest.param(
            "SHREK",
            {"age": (1, 2), "exit_code_to_state_map": [(0, 0)]},
            STRING_TABLE_1,
            [
                Result(state=State.OK, summary="Latest exit code: 0"),
                *_SHREK_METRIC_RESULTS_1,
                Result(state=State.OK, notice="Latest job started at 2019-01-12 14:53:21"),
                Result(
                    state=State.CRIT,
                    summary="Job age: 1 year 178 days (warn/crit at 1 second/2 seconds)",
                ),
                Metric("job_age", 46999419.0, levels=(1.0, 2.0), boundaries=(0.0, None)),
                *_SHREK_METRIC_RESULTS_2,
            ],
            id="old job",
        ),
        pytest.param(
            "SHREK",
            {"age": (0, 0), "exit_code_to_state_map": [(0, 1)]},
            STRING_TABLE_1,
            [
                Result(
                    state=State.WARN,
                    summary="Latest exit code: 0",
                ),
                *_SHREK_METRIC_RESULTS_1,
                Result(state=State.OK, notice="Latest job started at 2019-01-12 14:53:21"),
                Result(state=State.OK, summary="Job age: 1 year 178 days"),
                Metric("job_age", 46999419.0, boundaries=(0.0, None)),
                *_SHREK_METRIC_RESULTS_2,
            ],
            id="failed job",
        ),
        pytest.param(
            "SHREK",
            {"age": (1, 2), "exit_code_to_state_map": [(0, 0)]},
            STRING_TABLE_1_RUNNING,
            [
                Result(state=State.OK, summary="Latest exit code: 0"),
                *_SHREK_METRIC_RESULTS_1,
                Result(
                    state=State.OK,
                    notice=(
                        "6 jobs are currently running, started at"
                        " 2019-05-08 09:41:01, 2019-05-08 09:42:01,"
                        " 2019-05-08 09:43:01, 2019-05-08 09:44:01,"
                        " 2018-09-18 22:11:41, 2019-05-08 09:46:01"
                    ),
                ),
                Result(
                    state=State.CRIT,
                    summary=(
                        "Job age (currently running): "
                        "1 year 294 days (warn/crit at 1 second/2 seconds)"
                    ),
                ),
                # The age of the job that has been running the longest (started
                # 2018-09-18), not of the one that started last.
                Metric("job_age", 56999119.0, levels=(1.0, 2.0), boundaries=(0.0, None)),
                *_SHREK_METRIC_RESULTS_2,
            ],
            id="long running job",
        ),
    ],
)
def test_check_job(
    item: str,
    params: job.CheckParameters,
    string_table: StringTable,
    expected_results: Sequence[Result | Metric],
) -> None:
    section = job.parse_job(string_table)
    with time_machine.travel(datetime.datetime.fromtimestamp(TIME, tz=ZoneInfo("CET"))):
        assert list(job.check_job(item, params, section)) == expected_results


def test_discover():
    assert list(job.discover_job(job.parse_job(STRING_TABLE_RUNNING))) == [
        Service(item="230-testing-funning")
    ]


def test_parse_order():
    section = job.parse_job(STRING_TABLE_RUNNING)
    assert section["230-testing-funning"]["running"] is True

    section = job.parse_job(STRING_TABLE_RUNNING + STRING_TABLE_RUNNING_FINISHED_PART)
    assert section["230-testing-funning"]["running"] is True

    section = job.parse_job(STRING_TABLE_RUNNING_FINISHED_PART + STRING_TABLE_RUNNING)
    assert section["230-testing-funning"]["running"] is True

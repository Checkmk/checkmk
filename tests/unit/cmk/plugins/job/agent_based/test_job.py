#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
from collections.abc import Mapping, Sequence
from dataclasses import fields
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.job.agent_based import job
from cmk.plugins.job.lib import CheckParameters

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
    "SHREK": [
        job.CompletedJob(
            name="SHREK",
            start_time=1547301201.0,
            exit_code=0,
            metrics=job.Metrics(
                real_time=120.0,
                user_time=1.0,
                system_time=0.0,
                reads=0,
                writes=0,
                max_res_bytes=1234000,
                avg_mem_bytes=1000,
                invol_context_switches=12,
                vol_context_switches=23,
            ),
        ),
    ],
    "SNOWWHITE": [
        job.CompletedJob(
            name="SNOWWHITE",
            start_time=1557301201.0,
            exit_code=1,
            metrics=job.Metrics(
                real_time=360.0,
                user_time=0.0,
                system_time=0.0,
                reads=0,
                writes=0,
                max_res_bytes=2224000,
                avg_mem_bytes=0,
                invol_context_switches=1,
                vol_context_switches=2,
            ),
        ),
        job.RunningJob(name="SNOWWHITE", pid=27997, start_time=1557301261.0),
        job.RunningJob(name="SNOWWHITE", pid=28912, start_time=1557301321.0),
        job.RunningJob(name="SNOWWHITE", pid=29381, start_time=1557301381.0),
        job.RunningJob(name="SNOWWHITE", pid=30094, start_time=1557301441.0),
        job.RunningJob(name="SNOWWHITE", pid=30747, start_time=1537301501.0),
        job.RunningJob(name="SNOWWHITE", pid=31440, start_time=1557301561.0),
    ],
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
    "backup.sh": [
        job.CompletedJob(
            name="backup.sh",
            start_time=1415204091.0,
            exit_code=0,
            metrics=job.Metrics(
                real_time=281.65,
                user_time=277.7,
                system_time=32.12,
                reads=0,
                writes=251792,
                max_res_bytes=130304000,
                avg_mem_bytes=0,
                invol_context_switches=16806,
                vol_context_switches=32779,
            ),
        ),
        job.RunningJob(name="backup.sh", pid=None, start_time=1415205713.0),
    ],
    "cleanup_remote_logs": [
        job.CompletedJob(
            name="cleanup_remote_logs",
            start_time=1415153430.0,
            exit_code=0,
            metrics=job.Metrics(
                real_time=9.9,
                user_time=8.85,
                system_time=0.97,
                reads=96,
                writes=42016,
                max_res_bytes=11456000,
                avg_mem_bytes=0,
                invol_context_switches=15,
                vol_context_switches=274,
            ),
        ),
    ],
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
    "process1minrtu": [
        job.CompletedJob(
            name="process1minrtu",
            start_time=1560925321.0,
            exit_code=0,
            metrics=job.Metrics(
                real_time=2.63,
                user_time=0.62,
                system_time=0.31,
                reads=90736,
                writes=0,
                max_res_bytes=109380000,
                avg_mem_bytes=0,
                invol_context_switches=203407,
                vol_context_switches=2025,
            ),
        ),
        # The "process1minrtu.30166running" file was written by an agent predating
        # werk 15450, which is out of support - so it is taken at face value, stale
        # start time and all.
        job.RunningJob(name="process1minrtu", pid=30166, start_time=1560921361.0),
    ],
}

STRING_TABLE_RUNNING = [
    ["==>", "230-testing-funning.113660running", "<=="],
    ["start_time", "1730709681"],
]

STRING_TABLE_RUNNING_FINISHED_PART = [
    # the name deliberately ends in "running", see test_parse_header
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
    ["header", "expected_result"],
    [
        pytest.param(
            ["==>", "SHREK", "<=="],
            ("SHREK", job.RunState.COMPLETED, None),
            id="completed",
        ),
        pytest.param(
            ["==>", "SNOWWHITE.27997running", "<=="],
            ("SNOWWHITE", job.RunState.RUNNING, 27997),
            id="running with pid",
        ),
        pytest.param(
            ["==>", "backup.sh", "<=="],
            ("backup.sh", job.RunState.COMPLETED, None),
            id="dot in the job name",
        ),
        pytest.param(
            ["==>", "backup.sh.1234running", "<=="],
            ("backup.sh", job.RunState.RUNNING, 1234),
            id="dot in the job name, running",
        ),
        pytest.param(
            ["==>", "backup.sh.running", "<=="],
            ("backup.sh", job.RunState.RUNNING, None),
            id="running without pid (pre-1.6 mk-job)",
        ),
        pytest.param(
            ["==>", "IBM", "AIX", "7.3", "Weird", "Time", "Labels", "<=="],
            ("IBM AIX 7.3 Weird Time Labels", job.RunState.COMPLETED, None),
            id="blanks in the job name",
        ),
        pytest.param(
            # Only the ".<pid>running" suffix marks a running job, so a job whose
            # own name ends in "running" is not mistaken for one.
            ["==>", "230-testing-funning", "<=="],
            ("230-testing-funning", job.RunState.COMPLETED, None),
            id="job name ending in 'running'",
        ),
        pytest.param(
            ["==>", "just-running", "<=="],
            ("just-running", job.RunState.COMPLETED, None),
            id="job name ending in '-running'",
        ),
        pytest.param(
            ["==>", "<=="],
            None,
            id="no job name at all",
        ),
    ],
)
def test_parse_header(
    header: list[str], expected_result: tuple[str, job.RunState, int | None] | None
) -> None:
    assert job._parse_header(header) == expected_result


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
    ["values", "expected"],
    [
        pytest.param(
            {"real_time": "0:35", "user_time": "10", "system_time": "8.5"},
            job.Metrics(35.0, 10.0, 8.5, None, None, None, None, None, None),
            id="minimal",
        ),
        pytest.param(
            {"real_time": "0:35,1", "user_time": "10,1", "system_time": "8,5"},
            job.Metrics(35.1, 10.1, 8.5, None, None, None, None, None, None),
            id="localized-float",
        ),
        pytest.param(
            {
                "real_time": "0:35",
                "user_time": "10",
                "system_time": "8.5",
                "reads": "100",
                "writes": "50",
            },
            job.Metrics(35.0, 10.0, 8.5, 100, 50, None, None, None, None),
            id="reads-writes",
        ),
        pytest.param(
            {
                "real_time": "0:35",
                "user_time": "10",
                "system_time": "8.5",
                "max_res_kbytes": "2",
                "avg_mem_kbytes": "1",
            },
            job.Metrics(35.0, 10.0, 8.5, None, None, 2000, 1000, None, None),
            id="bytes",
        ),
        pytest.param(
            {
                "real_time": "0:35",
                "user_time": "10",
                "system_time": "8.5",
                "invol_context_switches": "0",
                "vol_context_switches": "0",
            },
            job.Metrics(35.0, 10.0, 8.5, None, None, None, None, 0, 0),
            id="ctx-switches",
        ),
        pytest.param(
            # /usr/bin/time is a separate package and may not be installed at all,
            # in which case mk-job writes nothing but the start time and the exit
            # code of the shell that failed to run it.
            {},
            job.Metrics(None, None, None, None, None, None, None, None, None),
            id="no metrics at all",
        ),
        pytest.param(
            # mk-job.aix and mk-job.solaris merge the job's own stderr into the
            # file, so any field may hold something that is not a number.
            {"real_time": "trouble ahead", "user_time": "10", "system_time": ""},
            job.Metrics(None, 10.0, None, None, None, None, None, None, None),
            id="unparsable values",
        ),
    ],
)
def test_metrics_from_dict(values: Mapping[str, str], expected: job.Metrics) -> None:
    assert job.Metrics.from_dict(values) == expected


def test_metric_specs_cover_all_metrics() -> None:
    # check_job renders every field of Metrics via _METRIC_SPECS, so a field
    # without an entry would only blow up while checking a service.
    assert {field.name for field in fields(job.Metrics)} == set(job._METRIC_SPECS)


def test_incomplete_information_results() -> None:
    results = (
        Result(
            state=State.UNKNOWN,
            summary="Got incomplete information for this job",
            details="No file of a completed run - this job has probably not finished one yet, or its file is gone.",
        ),
        Result(
            state=State.UNKNOWN,
            summary="Got incomplete information for this job",
            details="No exit code for the last completed run - its file is probably truncated.",
        ),
        Result(
            state=State.UNKNOWN,
            summary="Got incomplete information for this job",
            details="No start time for the last completed run - probably no perl on the monitored host.",
        ),
    )
    assert all(result.state is State.UNKNOWN for result in results)
    # The summary is deliberately the same for all of them - werk 22105 quotes it.
    assert {result.summary for result in results} == {"Got incomplete information for this job"}
    # What tells them apart is the details, one line each.
    assert len({result.details for result in results}) == len(results)
    assert all("\n" not in result.details for result in results)


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
            # The data of a ".<pid>running" file never replaces the data of the
            # completed job, whichever of the two started later.
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
                "killed_job": [
                    job.CompletedJob(
                        name="killed_job",
                        start_time=1560925321.0,
                        exit_code=0,
                        metrics=job.Metrics(2.63, None, None, None, None, None, None, None, None),
                    ),
                    job.RunningJob(name="killed_job", pid=30166, start_time=1560929999.0),
                ]
            },
            id="running file newer than the completed job",
        ),
        pytest.param(
            [
                ["==>", "killed_job.30166running", "<=="],
                ["start_time", "1560929999"],
                ["Command", "terminated", "by", "signal", "9"],
                ["exit_code", "0"],
                ["real", "1:32:44"],
            ],
            {"killed_job": [job.RunningJob(name="killed_job", pid=30166, start_time=1560929999.0)]},
            id="running file without a completed job",
        ),
        pytest.param(
            # mk-job versions that determine the timestamp via perl write a bare
            # "start_time " into the running file too if perl is not installed. We
            # know the job is running, but not since when.
            [
                ["==>", "no-perl.4711running", "<=="],
                ["start_time"],
            ],
            {"no-perl": [job.UndatedRunningFile(name="no-perl", pid=4711)]},
            id="running file without a usable start time",
        ),
        pytest.param(
            # Only a ".<pid>running" suffix marks a running file, so a job whose own
            # name ends in "running" keeps its data.
            [
                ["==>", "keep-running", "<=="],
                ["start_time", "1560925321"],
                ["exit_code", "0"],
            ],
            {
                "keep-running": [
                    job.CompletedJob(
                        name="keep-running",
                        start_time=1560925321.0,
                        exit_code=0,
                        metrics=job.Metrics(None, None, None, None, None, None, None, None, None),
                    ),
                ]
            },
            id="job name ending in 'running'",
        ),
        pytest.param(
            [
                [
                    "==>",
                    "empty_file.123running",
                    "<==",
                ]
            ],
            # An empty file has no start time either.
            {"empty_file": [job.UndatedRunningFile(name="empty_file", pid=123)]},
            id="empty running file",
        ),
        pytest.param(
            # An empty completed file, on the other hand, still describes a job -
            # we just know nothing about it. Dropping it would make its service
            # disappear instead of reporting that the data is incomplete.
            [["==>", "empty_file", "<=="]],
            {
                "empty_file": [
                    job.CompletedJob(
                        name="empty_file",
                        start_time=None,
                        exit_code=None,
                        metrics=job.Metrics(None, None, None, None, None, None, None, None, None),
                    ),
                ]
            },
            id="empty completed file",
        ),
        pytest.param(
            # /usr/bin/time is a separate package and may not be installed. mk-job
            # then reports the start time and the exit code of the shell that could
            # not run it, and nothing else.
            [
                ["==>", "no-usr-bin-time", "<=="],
                ["start_time", "1560925321"],
                ["exit_code", "127"],
            ],
            {
                "no-usr-bin-time": [
                    job.CompletedJob(
                        name="no-usr-bin-time",
                        start_time=1560925321.0,
                        exit_code=127,
                        metrics=job.Metrics(None, None, None, None, None, None, None, None, None),
                    ),
                ]
            },
            id="/usr/bin/time not installed",
        ),
        pytest.param(
            # mk-job.aix and mk-job.solaris merge the job's own stderr into the file,
            # so a metric may carry arbitrary text - which must not crash the parser.
            [
                ["==>", "noisy", "<=="],
                ["start_time", "1560925321"],
                ["real", "trouble", "ahead"],
                ["exit_code", "0"],
            ],
            {
                "noisy": [
                    job.CompletedJob(
                        name="noisy",
                        start_time=1560925321.0,
                        exit_code=0,
                        metrics=job.Metrics(None, None, None, None, None, None, None, None, None),
                    ),
                ]
            },
            id="job stderr merged into the metrics",
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
                "bla": [
                    job.CompletedJob(
                        name="bla",
                        start_time=None,
                        exit_code=None,
                        metrics=job.Metrics(
                            real_time=5564.0,
                            user_time=2249.08,
                            system_time=334.76,
                            reads=None,
                            writes=None,
                            max_res_bytes=None,
                            avg_mem_bytes=None,
                            invol_context_switches=None,
                            vol_context_switches=None,
                        ),
                    ),
                ]
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
                "bla": [
                    job.CompletedJob(
                        name="bla",
                        start_time=None,
                        exit_code=None,
                        metrics=job.Metrics(
                            real_time=None,
                            user_time=2249.08,
                            system_time=None,
                            reads=None,
                            writes=None,
                            max_res_bytes=None,
                            avg_mem_bytes=None,
                            invol_context_switches=None,
                            vol_context_switches=None,
                        ),
                    ),
                ]
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
                "IBM AIX 7.3 Weird Time Labels": [
                    job.CompletedJob(
                        name="IBM AIX 7.3 Weird Time Labels",
                        start_time=1776568200.0,
                        exit_code=0,
                        metrics=job.Metrics(
                            real_time=1.28,
                            user_time=0.48,
                            system_time=0.02,
                            reads=None,
                            writes=None,
                            max_res_bytes=None,
                            avg_mem_bytes=None,
                            invol_context_switches=None,
                            vol_context_switches=None,
                        ),
                    ),
                ]
            },
            id="AIX time output with capitalized labels",
        ),
        pytest.param(
            # mk-job versions that determine the timestamp via perl write a bare
            # "start_time " if perl is not installed, so there is no timestamp to
            # parse.
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
                "Cleanup-Cache-Files": [
                    job.CompletedJob(
                        name="Cleanup-Cache-Files",
                        exit_code=0,
                        start_time=None,
                        metrics=job.Metrics(
                            real_time=0.96,
                            user_time=0.11,
                            system_time=0.5,
                            reads=4608,
                            writes=24,
                            max_res_bytes=25216000,
                            avg_mem_bytes=0,
                            invol_context_switches=940,
                            vol_context_switches=99,
                        ),
                    ),
                ]
            },
            id="start_time without a value",
        ),
    ],
)
def test_parse(string_table: StringTable, expected_parsed_data: job.Section) -> None:
    assert job.parse_job(string_table) == expected_parsed_data


def _undated_result(pids: list[int | None]) -> Result:
    """What check_job yields for the running files it cannot date."""
    count = len(pids)
    _pids = ", ".join(str(pid) for pid in pids if pid is not None)
    return Result(
        state=State.WARN,
        summary=(
            f"{count} running file{'' if count == 1 else 's'} without a usable start"
            f" time{f' (PID {_pids})' if _pids else ''}"
        ),
        details="To fix this start time issue, please update the agent or install perl on the host",
    )


# The metrics of SECTION_1["SHREK"], in the order check_job emits them.
_SHREK_METRIC_RESULTS: Sequence[Result | Metric] = [
    Result(state=State.OK, summary="Real time: 2 minutes 0 seconds"),
    Metric("real_time", 120.0, boundaries=(0.0, None)),
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
            job.check_plugin_job.check_default_parameters,
            STRING_TABLE_1,
            [
                Result(state=State.OK, summary="Latest exit code: 0"),
                *_SHREK_METRIC_RESULTS,
                Result(state=State.OK, notice="Latest job started at 2019-01-12 14:53:21"),
                Result(state=State.OK, summary="Job age: 1 year 178 days"),
                Metric("job_age", 46999419.0, boundaries=(0.0, None)),
            ],
            id="no age levels configured",
        ),
        pytest.param(
            "cleanup_remote_logs",
            job.check_plugin_job.check_default_parameters,
            STRING_TABLE_2,
            [
                Result(state=State.OK, summary="Latest exit code: 0"),
                Result(state=State.OK, summary="Real time: 10 seconds"),
                Metric("real_time", 9.9, boundaries=(0.0, None)),
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
                Result(state=State.OK, notice="Latest job started at 2014-11-05 03:10:30"),
                Result(state=State.OK, summary="Job age: 5 years 248 days"),
                Metric("job_age", 179147190.0, boundaries=(0.0, None)),
            ],
            id="completed job with all metrics",
        ),
        pytest.param(
            "backup.sh",
            {
                "age": ("fixed", (1.0, 2.0)),
                "exit_code_to_state_map": [{"exit_code": 0, "state": 0}],
            },
            STRING_TABLE_2,
            [
                Result(state=State.OK, summary="Latest exit code: 0"),
                Result(state=State.OK, summary="Real time: 4 minutes 42 seconds"),
                Metric("real_time", 281.65, boundaries=(0.0, None)),
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
                Result(
                    state=State.OK,
                    notice="1 job is currently running, started at 2014-11-05 17:41:53",
                ),
                Result(
                    state=State.CRIT,
                    summary="Job age (currently running): 5 years 247 days (warn/crit at 1 second/2 seconds)",
                ),
                Metric("job_age", 179094907.0, levels=(1.0, 2.0), boundaries=(0.0, None)),
            ],
            id="age levels breached while one job is running",
        ),
        pytest.param(
            "missing",
            {
                "age": ("fixed", (1.0, 2.0)),
                "exit_code_to_state_map": [{"exit_code": 0, "state": 0}],
            },
            STRING_TABLE_2,
            [],
            id="item not in section",
        ),
        pytest.param(
            "Cleanup-Cache-Files",
            job.check_plugin_job.check_default_parameters,
            [
                ["==>", "Cleanup-Cache-Files", "<=="],
                ["real_time", "0.96"],
                ["exit_code", "0"],
            ],
            [
                Result(state=State.OK, summary="Latest exit code: 0"),
                Result(state=State.OK, summary="Real time: 960 milliseconds"),
                Metric("real_time", 0.96, boundaries=(0.0, None)),
                Result(
                    state=State.UNKNOWN,
                    summary="Got incomplete information for this job",
                    details="No start time for the last completed run - probably no perl on the monitored host.",
                ),
            ],
            id="job without a start time",
        ),
        pytest.param(
            # The outcome does not depend on the start time, so a job that failed is
            # CRIT and not UNKNOWN even if we cannot say when it ran.
            "Cleanup-Cache-Files",
            job.check_plugin_job.check_default_parameters,
            [["==>", "Cleanup-Cache-Files", "<=="], ["exit_code", "1"]],
            [
                Result(state=State.CRIT, summary="Latest exit code: 1"),
                Result(
                    state=State.UNKNOWN,
                    summary="Got incomplete information for this job",
                    details="No start time for the last completed run - probably no perl on the monitored host.",
                ),
            ],
            id="failed job without a start time",
        ),
        pytest.param(
            # mk-job appends the exit code to the file of a completed run last, so a
            # file that was cut short has everything but that.
            "Cleanup-Cache-Files",
            job.check_plugin_job.check_default_parameters,
            [
                ["==>", "Cleanup-Cache-Files", "<=="],
                ["start_time", str(TIME - 60)],
                ["real", "0.96"],
                ["user", "0.96"],
                ["sys", "0.96"],
            ],
            [
                Result(
                    state=State.UNKNOWN,
                    summary="Got incomplete information for this job",
                    details="No exit code for the last completed run - its file is probably truncated.",
                )
            ],
            id="job without an exit code",
        ),
        pytest.param(
            # Werk 22105: the start time of the completed job is only needed while
            # nothing is running - a running job supplies one of its own.
            "Cleanup-Cache-Files",
            job.check_plugin_job.check_default_parameters,
            [
                ["==>", "Cleanup-Cache-Files", "<=="],
                ["real", "0.96"],
                ["exit_code", "0"],
                ["==>", "Cleanup-Cache-Files.running", "<=="],
                ["start_time", str(int(TIME) - 60)],
            ],
            [
                Result(state=State.OK, summary="Latest exit code: 0"),
                Result(state=State.OK, summary="Real time: 960 milliseconds"),
                Metric("real_time", 0.96, boundaries=(0.0, None)),
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
            {
                "age": ("fixed", (1.0, 2.0)),
                "exit_code_to_state_map": [{"exit_code": 0, "state": 0}],
            },
            STRING_TABLE_1,
            [
                Result(state=State.OK, summary="Latest exit code: 0"),
                *_SHREK_METRIC_RESULTS,
                Result(state=State.OK, notice="Latest job started at 2019-01-12 14:53:21"),
                Result(
                    state=State.CRIT,
                    summary="Job age: 1 year 178 days (warn/crit at 1 second/2 seconds)",
                ),
                Metric("job_age", 46999419.0, levels=(1.0, 2.0), boundaries=(0.0, None)),
            ],
            id="old job",
        ),
        pytest.param(
            "SHREK",
            {"age": None, "exit_code_to_state_map": [{"exit_code": 0, "state": 1}]},
            STRING_TABLE_1,
            [
                Result(
                    state=State.WARN,
                    summary="Latest exit code: 0",
                ),
                *_SHREK_METRIC_RESULTS,
                Result(state=State.OK, notice="Latest job started at 2019-01-12 14:53:21"),
                Result(state=State.OK, summary="Job age: 1 year 178 days"),
                Metric("job_age", 46999419.0, boundaries=(0.0, None)),
            ],
            id="failed job",
        ),
        pytest.param(
            "SHREK",
            {
                "age": ("fixed", (1.0, 2.0)),
                "exit_code_to_state_map": [{"exit_code": 0, "state": 0}],
            },
            STRING_TABLE_1_RUNNING,
            [
                Result(state=State.OK, summary="Latest exit code: 0"),
                *_SHREK_METRIC_RESULTS,
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
            ],
            id="long running job",
        ),
        pytest.param(
            "SNOWWHITE",
            job.check_plugin_job.check_default_parameters,
            STRING_TABLE_1,
            [
                # exit code 1 is not in the map, so it falls back to CRIT
                Result(state=State.CRIT, summary="Latest exit code: 1"),
                Result(state=State.OK, summary="Real time: 6 minutes 0 seconds"),
                Metric("real_time", 360.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="User time: 0 seconds"),
                Metric("user_time", 0.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="System time: 0 seconds"),
                Metric("system_time", 0.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Filesystem reads: 0"),
                Metric("reads", 0.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Filesystem writes: 0"),
                Metric("writes", 0.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Max. memory: 2.12 MiB"),
                Metric("max_res_bytes", 2224000.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Avg. memory: 0 B"),
                Metric("avg_mem_bytes", 0.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Invol. context switches: 1"),
                Metric("invol_context_switches", 1.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Vol. context switches: 2"),
                Metric("vol_context_switches", 2.0, boundaries=(0.0, None)),
                Result(
                    state=State.OK,
                    notice=(
                        "6 jobs are currently running, started at"
                        " 2019-05-08 09:41:01, 2019-05-08 09:42:01,"
                        " 2019-05-08 09:43:01, 2019-05-08 09:44:01,"
                        " 2018-09-18 22:11:41, 2019-05-08 09:46:01"
                    ),
                ),
                # the age is computed from the *oldest* running job (2018-09-18)
                Result(state=State.OK, summary="Job age (currently running): 1 year 294 days"),
                Metric("job_age", 56999119.0, boundaries=(0.0, None)),
            ],
            id="unmapped exit code and several running jobs",
        ),
        pytest.param(
            # /usr/bin/time is a separate package and may not be installed, in which
            # case mk-job reports the start time and exit code 127 and nothing else.
            "no-usr-bin-time",
            job.check_plugin_job.check_default_parameters,
            [
                ["==>", "no-usr-bin-time", "<=="],
                ["start_time", str(TIME - 60)],
                ["exit_code", "127"],
            ],
            [
                Result(state=State.CRIT, summary="Latest exit code: 127"),
                Result(state=State.OK, notice="Latest job started at 2020-07-09 15:16:00"),
                Result(state=State.OK, summary="Job age: 1 minute 0 seconds"),
                Metric("job_age", 60.0, boundaries=(0.0, None)),
            ],
            id="completed job without any metrics",
        ),
        pytest.param(
            # An empty file yields a job we know nothing about - not even its exit code.
            "empty-file",
            job.check_plugin_job.check_default_parameters,
            [
                ["==>", "empty-file", "<=="],
            ],
            [
                Result(
                    state=State.UNKNOWN,
                    summary="Got incomplete information for this job",
                    details="No exit code for the last completed run - its file is probably truncated.",
                )
            ],
            id="completed job from an empty file",
        ),
        pytest.param(
            # A job that is running but has never completed has no exit code. That is
            # not incomplete data - there is simply no outcome to report yet.
            "never-completed",
            job.check_plugin_job.check_default_parameters,
            [["==>", "never-completed.1234running", "<=="], ["start_time", str(TIME - 60)]],
            [
                Result(
                    state=State.OK,
                    notice="1 job is currently running, started at 2020-07-09 15:16:00",
                ),
                Result(state=State.OK, summary="Job age (currently running): 1 minute 0 seconds"),
                Metric("job_age", 60.0, boundaries=(0.0, None)),
            ],
            id="running job without a completed one",
        ),
        pytest.param(
            # The age levels apply to a job that has never completed, too.
            "never-completed",
            {
                "age": ("fixed", (1.0, 2.0)),
                "exit_code_to_state_map": [{"exit_code": 0, "state": 0}],
            },
            [
                ["==>", "never-completed.1234running", "<=="],
                ["start_time", str(TIME - 60)],
            ],
            [
                Result(
                    state=State.OK,
                    notice="1 job is currently running, started at 2020-07-09 15:16:00",
                ),
                Result(
                    state=State.CRIT,
                    summary=(
                        "Job age (currently running): 1 minute 0 seconds"
                        " (warn/crit at 1 second/2 seconds)"
                    ),
                ),
                Metric("job_age", 60.0, levels=(1.0, 2.0), boundaries=(0.0, None)),
            ],
            id="running job without a completed one, age levels breached",
        ),
        pytest.param(
            # On a host without perl, one running file may carry a usable start time
            # while another does not.
            "no-perl",
            job.check_plugin_job.check_default_parameters,
            [
                ["==>", "no-perl.1234running", "<=="],
                ["start_time", str(TIME - 60)],
                ["==>", "no-perl.4711running", "<=="],
                ["start_time"],
            ],
            [
                _undated_result(
                    [
                        4711,
                    ]
                ),
                Result(
                    state=State.OK,
                    notice="1 job is currently running, started at 2020-07-09 15:16:00",
                ),
                Result(state=State.OK, summary="Job age (currently running): 1 minute 0 seconds"),
                Metric("job_age", 60.0, boundaries=(0.0, None)),
            ],
            id="running job with an unusable file next to it",
        ),
        pytest.param(
            "Cleanup-Cache-Files",
            job.check_plugin_job.check_default_parameters,
            [
                ["==>", "Cleanup-Cache-Files", "<=="],
                ["start_time", str(TIME - 120)],
                ["exit_code", "0"],
                ["real_time", "0.96"],
                ["user_time", "0.96"],
                ["system_time", "0.96"],
                ["==>", "Cleanup-Cache-Files.1234running", "<=="],
                ["start_time", str(TIME - 60)],
            ],
            [
                Result(state=State.OK, summary="Latest exit code: 0"),
                Result(state=State.OK, summary="Real time: 960 milliseconds"),
                Metric("real_time", 0.96, boundaries=(0.0, None)),
                Result(state=State.OK, notice="User time: 960 milliseconds"),
                Metric("user_time", 0.96, boundaries=(0.0, None)),
                Result(state=State.OK, notice="System time: 960 milliseconds"),
                Metric("system_time", 0.96, boundaries=(0.0, None)),
                Result(
                    state=State.OK,
                    notice="1 job is currently running, started at 2020-07-09 15:16:00",
                ),
                Result(state=State.OK, summary="Job age (currently running): 1 minute 0 seconds"),
                Metric("job_age", 60.0, boundaries=(0.0, None)),
            ],
            id="completed job with only some metrics, one running job",
        ),
        pytest.param(
            # The last completed run is still reported; only the file we cannot date
            # is flagged.
            "no-perl",
            job.check_plugin_job.check_default_parameters,
            [
                ["==>", "no-perl", "<=="],
                ["start_time", str(TIME - 120)],
                ["exit_code", "0"],
                ["==>", "no-perl.30166running", "<=="],
                ["start_time"],
            ],
            [
                _undated_result(
                    [
                        30166,
                    ]
                ),
                Result(state=State.OK, summary="Latest exit code: 0"),
                Result(state=State.OK, notice="Latest job started at 2020-07-09 15:15:00"),
                Result(state=State.OK, summary="Job age: 2 minutes 0 seconds"),
                Metric("job_age", 120.0, boundaries=(0.0, None)),
            ],
            id="undated running file next to a completed job",
        ),
        pytest.param(
            # Pre-1.6 mk-job left the pid out of the file name.
            "no-perl-only",
            job.check_plugin_job.check_default_parameters,
            [["==>", "no-perl-only.running", "<=="], ["start_time"]],
            [
                _undated_result([None]),
                Result(
                    state=State.UNKNOWN,
                    summary="Got incomplete information for this job",
                    details="No file of a completed run - this job has probably not finished one yet, or its file is gone.",
                ),
            ],
            id="undated running file and nothing else",
        ),
        pytest.param(
            "several-undated",
            job.check_plugin_job.check_default_parameters,
            [
                ["==>", "several-undated.1running", "<=="],
                ["start_time"],
                ["==>", "several-undated.2running", "<=="],
                ["start_time"],
            ],
            [
                _undated_result([1, 2]),
                Result(
                    state=State.UNKNOWN,
                    summary="Got incomplete information for this job",
                    details="No file of a completed run - this job has probably not finished one yet, or its file is gone.",
                ),
            ],
            id="several undated running files",
        ),
        pytest.param(
            # An age of exactly zero is an age, not a start time in the future.
            "just-started",
            job.check_plugin_job.check_default_parameters,
            [
                ["==>", "just-started", "<=="],
                ["start_time", str(TIME)],
                ["exit_code", "0"],
            ],
            [
                Result(state=State.OK, summary="Latest exit code: 0"),
                Result(state=State.OK, notice="Latest job started at 2020-07-09 15:17:00"),
                Result(state=State.OK, summary="Job age: 0 seconds"),
                Metric("job_age", 0.0, boundaries=(0.0, None)),
            ],
            id="job age of exactly zero",
        ),
        pytest.param(
            "future",
            job.check_plugin_job.check_default_parameters,
            [["==>", "future", "<=="], ["start_time", str(TIME + 3600)], ["exit_code", "0"]],
            [
                Result(state=State.OK, summary="Latest exit code: 0"),
                Result(state=State.OK, notice="Latest job started at 2020-07-09 16:17:00"),
                Result(
                    state=State.OK,
                    summary=(
                        "Job age appears to be 1 hour 0 minutes in the future (check your system time)"
                    ),
                ),
            ],
            id="job started in the future",
        ),
    ],
)
def test_check_job(
    item: str,
    params: CheckParameters,
    string_table: StringTable,
    expected_results: Sequence[Result | Metric],
) -> None:
    section = job.parse_job(string_table)
    with time_machine.travel(datetime.datetime.fromtimestamp(TIME, tz=ZoneInfo("CET"))):
        assert list(job.check_job(item, params, section)) == expected_results


def test_discover() -> None:
    assert list(job.discover_job(job.parse_job(STRING_TABLE_RUNNING))) == [
        Service(item="230-testing-funning")
    ]


def test_parse_order() -> None:
    # The agent collects the files of this section with "find", which does not sort
    # them, so either order can turn up - and both must yield the same jobs.
    completed = job.CompletedJob(
        name="230-testing-funning",
        start_time=1730702588.0,
        exit_code=0,
        metrics=job.Metrics(
            real_time=2.0,
            user_time=0.0,
            system_time=0.0,
            reads=0,
            writes=0,
            max_res_bytes=2304000,
            avg_mem_bytes=0,
            invol_context_switches=0,
            vol_context_switches=2,
        ),
    )
    running = job.RunningJob(name="230-testing-funning", pid=113660, start_time=1730709681.0)

    assert job.parse_job(STRING_TABLE_RUNNING) == {"230-testing-funning": [running]}

    assert job.parse_job(STRING_TABLE_RUNNING + STRING_TABLE_RUNNING_FINISHED_PART) == {
        "230-testing-funning": [running, completed]
    }

    assert job.parse_job(STRING_TABLE_RUNNING_FINISHED_PART + STRING_TABLE_RUNNING) == {
        "230-testing-funning": [completed, running]
    }

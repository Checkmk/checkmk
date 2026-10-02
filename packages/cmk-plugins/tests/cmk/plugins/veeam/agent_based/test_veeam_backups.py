#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json

import pytest
import time_machine

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.plugins.veeam.agent_based.veeam_backups import (
    BackupTask,
    check_veeam_backups,
    CheckParameters,
    discovery_veeam_backups,
    monitoring_state,
    parse_veeam_backups,
)

PARAMS: CheckParameters = {"age": ("fixed", (20.0, 40.0))}
END_TIME = "2019-01-21T00:29:12.473+03:00"


def _task(
    job_name: str,
    progress: dict[str, object] | None | bool = False,
    **overrides: object,
) -> str:
    task_dict: dict[str, object] = {
        "jobName": job_name,
        "state": "Stopped",
        "result": {"result": "Success"},
        "endTime": END_TIME,
    }
    if progress is not False:
        task_dict["progress"] = progress
    task_dict.update(overrides)
    return json.dumps(task_dict)


STRING_TABLE = [
    [
        _task(
            "Daily_VM_Backup",
            progress={
                "duration": "0.00:18:50",
                "processingRate": "41943040",
                "processedSize": 107374182400,
                "readSize": 53687091200,
                "transferredSize": 21474836480,
            },
        )
    ],
    [_task("warning_backup", result={"result": "Warning"})],
    [_task("running_backup", state="Working", result={"result": "None"})],
    [_task("failed_backup", result={"result": "Failed", "message": "Network error"})],
]


def test_discovery_veeam_backups() -> None:
    section = parse_veeam_backups(STRING_TABLE)
    assert list(discovery_veeam_backups(section)) == [
        Service(item="Daily_VM_Backup"),
        Service(item="warning_backup"),
        Service(item="running_backup"),
        Service(item="failed_backup"),
    ]


def test_discovered_item_is_the_sanitized_job_name() -> None:
    section = parse_veeam_backups([[_task("Bob's nightly VMs")]])

    assert list(discovery_veeam_backups(section)) == [Service(item="Bob_s_nightly_VMs")]


def test_check_veeam_backups_success() -> None:
    section = parse_veeam_backups(STRING_TABLE)
    results = list(check_veeam_backups("Daily_VM_Backup", PARAMS, section))
    assert results[0] == Result(state=State.OK, summary="Status: Success")
    assert Metric("totalsize", 107374182400) in results
    assert Metric("readsize", 53687091200) in results
    assert Metric("transferredsize", 21474836480) in results
    assert Metric("avgspeed", 41943040.0) in results
    assert Metric("duration", 1130.0) in results
    assert any(
        r.summary.startswith("Time since last backup:") for r in results if isinstance(r, Result)
    )


def test_check_veeam_backups_warning() -> None:
    section = parse_veeam_backups(STRING_TABLE)
    results = list(check_veeam_backups("warning_backup", PARAMS, section))
    assert results[0] == Result(state=State.WARN, summary="Status: Warning")


def test_check_veeam_backups_failed_shows_message() -> None:
    section = parse_veeam_backups(STRING_TABLE)
    results = list(check_veeam_backups("failed_backup", PARAMS, section))
    assert results[0] == Result(state=State.CRIT, summary="Status: Failed (Network error)")


def test_check_veeam_backups_end_time_in_future_is_unknown() -> None:
    section = parse_veeam_backups(
        [[_task("future_backup", endTime="2999-01-21T00:29:12.473+03:00")]]
    )
    results = list(check_veeam_backups("future_backup", PARAMS, section))
    assert Result(state=State.UNKNOWN, summary="Last backup: end time is in the future") in results


def test_check_veeam_backups_running_raises_ignore_results() -> None:
    section = parse_veeam_backups(STRING_TABLE)
    with pytest.raises(IgnoreResultsError):
        list(check_veeam_backups("running_backup", PARAMS, section))


@pytest.mark.parametrize(
    "seconds_after_end, expected_age_result",
    [
        pytest.param(
            10,
            Result(state=State.OK, summary="Time since last backup: 10 seconds"),
            id="age within the levels",
        ),
        pytest.param(
            30,
            Result(
                state=State.WARN,
                summary="Time since last backup: 30 seconds (warn/crit at 20 seconds/40 seconds)",
            ),
            id="age above the warn level",
        ),
        pytest.param(
            50,
            Result(
                state=State.CRIT,
                summary="Time since last backup: 50 seconds (warn/crit at 20 seconds/40 seconds)",
            ),
            id="age above the crit level",
        ),
    ],
)
def test_last_backup_age_is_rated_against_the_levels(
    seconds_after_end: int, expected_age_result: Result
) -> None:
    section = parse_veeam_backups([[_task("job")]])
    now = datetime.datetime.fromisoformat(END_TIME) + datetime.timedelta(seconds=seconds_after_end)

    with time_machine.travel(now, tick=False):
        results = list(check_veeam_backups("job", PARAMS, section))

    assert results == [Result(state=State.OK, summary="Status: Success"), expected_age_result]


def test_finished_backup_without_end_time_is_crit() -> None:
    section = parse_veeam_backups([[_task("job", endTime=None)]])

    results = list(check_veeam_backups("job", PARAMS, section))

    assert Result(state=State.CRIT, summary="No complete backup") in results


def test_unparsable_end_time_is_unknown() -> None:
    section = parse_veeam_backups([[_task("job", endTime="garbage")]])

    results = list(check_veeam_backups("job", PARAMS, section))

    assert results == [
        Result(state=State.OK, summary="Status: Success"),
        Result(state=State.UNKNOWN, summary="FAILED TO PARSE -> End time: (garbage)"),
    ]


def test_check_veeam_backups_vanished_task_goes_stale() -> None:
    section = parse_veeam_backups(STRING_TABLE)
    assert list(check_veeam_backups("no_longer_reported", PARAMS, section)) == []


def test_check_veeam_backups_running_suppresses_duration_and_age() -> None:
    section = parse_veeam_backups(
        [
            [
                _task(
                    "in_progress",
                    state="Working",
                    result={"result": "Success"},
                    progress={"duration": "0.00:05:00"},
                )
            ]
        ]
    )
    results = list(check_veeam_backups("in_progress", PARAMS, section))
    assert not any("Duration" in r.summary for r in results if isinstance(r, Result))
    assert not any("Time since last backup" in r.summary for r in results if isinstance(r, Result))


def test_check_veeam_backups_unparsable_processing_rate_is_shown_without_metric() -> None:
    section = parse_veeam_backups([[_task("odd_rate", progress={"processingRate": "40 MB/s"})]])
    results = list(check_veeam_backups("odd_rate", PARAMS, section))
    assert Result(state=State.OK, summary="FAILED TO PARSE -> Average speed: (40 MB/s)") in results
    assert not any(isinstance(r, Metric) and r.name == "avgspeed" for r in results)


def test_parse_veeam_backups() -> None:
    section = parse_veeam_backups([[_task("job")]])
    assert section == {
        "job": BackupTask(
            state="Stopped",
            result="Success",
            result_message=None,
            total_size=None,
            read_size=None,
            transferred_size=None,
            duration=None,
            processing_rate=None,
            end_time=END_TIME,
        )
    }


@pytest.mark.parametrize(
    "state, result, expected",
    [
        pytest.param("Stopped", "Success", State.OK, id="succeeded"),
        pytest.param("Stopped", "Warning", State.WARN, id="finished with warning"),
        pytest.param("Stopped", "Failed", State.CRIT, id="failed"),
        pytest.param("Stopped", "Kaputt", State.UNKNOWN, id="unparsable result"),
        pytest.param("Stopped", "None", State.UNKNOWN, id="terminal but no result"),
    ],
)
def test_monitoring_state(state: str, result: str, expected: State) -> None:
    assert monitoring_state(state, result) == expected


@pytest.mark.parametrize(
    "state", ["Working", "Starting", "Stopping", "Idle", "Postprocessing", "WaitingTape"]
)
def test_monitoring_state_active_raises_ignore_results(state: str) -> None:
    with pytest.raises(IgnoreResultsError):
        monitoring_state(state, "None")

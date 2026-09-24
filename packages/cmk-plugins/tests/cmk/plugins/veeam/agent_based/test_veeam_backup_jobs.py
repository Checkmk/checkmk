#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from datetime import datetime

import pytest

from cmk.agent_based.v2 import Metric, render, Result, Service, State
from cmk.plugins.veeam.agent_based.veeam_backup_jobs import (
    BackupJob,
    check_veeam_backup_jobs,
    discovery_veeam_backup_jobs,
    monitoring_state,
    parse_dotnet_timespan_seconds,
    parse_iso8601_epoch,
    parse_veeam_backup_jobs,
)


def _job(
    name: str,
    session_progress: dict[str, object] | None | bool = False,
    **overrides: object,
) -> str:
    job_dict = {
        "name": name,
        "type": "Backup",
        "status": "Inactive",
        "lastRun": "2019-01-21T00:10:22.473+03:00",
        "lastResult": "Success",
        "nextRun": "2019-01-22T00:10:00.000+03:00",
        "workload": "vm",
        "repositoryName": "Default Backup Repository",
        "objectsCount": 4,
    }
    if session_progress is not False:
        job_dict["sessionProgress"] = session_progress
    job_dict.update(overrides)
    return json.dumps(job_dict)


STRING_TABLE = [
    [_job("VMware_Server", session_progress={"duration": "0.00:18:50"})],
    [_job("warning_backup", lastResult="Warning")],
    [_job("backup_sync_job", type="BackupSync", status="Running", lastResult="None")],
    [
        _job(
            "never_run",
            status="Inactive",
            lastRun=None,
            lastResult="None",
            repositoryName=None,
            objectsCount=0,
        )
    ],
    [_job("stopped_and_failed", lastResult="Failed")],
    [_job("unknown_type", type="Unknown")],
]


def test_discovery_veeam_backup_jobs() -> None:
    section = parse_veeam_backup_jobs(STRING_TABLE)
    assert list(discovery_veeam_backup_jobs(section)) == [
        Service(item="VMware_Server"),
        Service(item="warning_backup"),
        Service(item="backup_sync_job"),
        Service(item="never_run"),
        Service(item="stopped_and_failed"),
        Service(item="unknown_type"),
    ]


def test_check_veeam_backup_jobs_success() -> None:
    section = parse_veeam_backup_jobs(STRING_TABLE)
    last_run_epoch = parse_iso8601_epoch("2019-01-21T00:10:22.473+03:00")
    next_run_epoch = parse_iso8601_epoch("2019-01-22T00:10:00.000+03:00")
    assert last_run_epoch is not None
    assert next_run_epoch is not None
    last_run = render.datetime(last_run_epoch)
    next_run = render.datetime(next_run_epoch)
    assert list(check_veeam_backup_jobs("VMware_Server", section)) == [
        Result(state=State.OK, summary="Status: Inactive, Result: Success"),
        Result(state=State.OK, summary=f"Last run: {last_run}"),
        Result(state=State.OK, summary="Duration: 18 minutes 50 seconds"),
        Metric("duration", 1130.0),
        Result(state=State.OK, summary=f"Next run: {next_run}"),
        Result(state=State.OK, summary="Target repository: Default Backup Repository"),
        Result(state=State.OK, summary="Objects: 4"),
        Result(state=State.OK, summary="Type: Backup"),
    ]


def test_parse_veeam_backup_jobs_unparsable_duration_becomes_none() -> None:
    section = parse_veeam_backup_jobs(
        [[_job("odd_duration", session_progress={"duration": "not-a-timespan"})]]
    )
    assert section["odd_duration"].duration is None


def test_check_veeam_backup_jobs_no_session_progress_omits_duration() -> None:
    section = parse_veeam_backup_jobs([[_job("no_progress", session_progress=None)]])
    results = list(check_veeam_backup_jobs("no_progress", section))
    assert not any("Duration" in r.summary for r in results if isinstance(r, Result))


def test_check_veeam_backup_jobs_warning() -> None:
    section = parse_veeam_backup_jobs(STRING_TABLE)
    results = list(check_veeam_backup_jobs("warning_backup", section))
    assert results[0] == Result(state=State.WARN, summary="Status: Inactive, Result: Warning")


def test_check_veeam_backup_jobs_failed() -> None:
    section = parse_veeam_backup_jobs(STRING_TABLE)
    results = list(check_veeam_backup_jobs("stopped_and_failed", section))
    assert results[0] == Result(state=State.CRIT, summary="Status: Inactive, Result: Failed")


def test_check_veeam_backup_jobs_never_run() -> None:
    section = parse_veeam_backup_jobs(STRING_TABLE)
    results = list(check_veeam_backup_jobs("never_run", section))
    assert results[0] == Result(state=State.OK, summary="No run has happened yet")
    next_run_epoch = parse_iso8601_epoch("2019-01-22T00:10:00.000+03:00")
    assert next_run_epoch is not None
    assert Result(state=State.OK, summary=f"Next run: {render.datetime(next_run_epoch)}") in results


def test_check_veeam_backup_jobs_unknown_type_still_renders() -> None:
    section = parse_veeam_backup_jobs(STRING_TABLE)
    results = list(check_veeam_backup_jobs("unknown_type", section))
    assert Result(state=State.OK, summary="Type: Unknown") in results


def test_check_veeam_backup_jobs_running_with_no_result_is_ok() -> None:
    section = parse_veeam_backup_jobs(STRING_TABLE)
    results = list(check_veeam_backup_jobs("backup_sync_job", section))
    assert results[0] == Result(state=State.OK, summary="Status: Running, Result: None")


def test_check_veeam_backup_jobs_vanished_job_goes_stale() -> None:
    section = parse_veeam_backup_jobs(STRING_TABLE)
    assert list(check_veeam_backup_jobs("no_longer_reported", section)) == []


def test_parse_veeam_backup_jobs() -> None:
    section = parse_veeam_backup_jobs([[_job("job", session_progress=None)]])
    assert section == {
        "job": BackupJob(
            job_type="Backup",
            status="Inactive",
            last_run=parse_iso8601_epoch("2019-01-21T00:10:22.473+03:00"),
            last_result="Success",
            next_run=parse_iso8601_epoch("2019-01-22T00:10:00.000+03:00"),
            workload="vm",
            repository_name="Default Backup Repository",
            objects_count=4,
            duration=None,
        )
    }


@pytest.mark.parametrize(
    "value, expected_epoch",
    [
        pytest.param(
            "2024-02-04T21:40:34.473+03:00",
            datetime.fromisoformat("2024-02-04T21:40:34.473+03:00").timestamp(),
            id="with fractional seconds",
        ),
        pytest.param("garbage", None, id="unparsable"),
    ],
)
def test_parse_iso8601_epoch(value: str, expected_epoch: float | None) -> None:
    assert parse_iso8601_epoch(value) == expected_epoch


@pytest.mark.parametrize(
    "last_result, expected",
    [
        pytest.param("Success", State.OK, id="succeeded"),
        pytest.param("Warning", State.WARN, id="finished with warning"),
        pytest.param("Failed", State.CRIT, id="failed"),
        pytest.param("Kaputt", State.UNKNOWN, id="unparsable result"),
        pytest.param("None", State.OK, id="no result yet"),
    ],
)
def test_monitoring_state(last_result: str, expected: State) -> None:
    assert monitoring_state(last_result) == expected


@pytest.mark.parametrize(
    "duration, expected_seconds",
    [
        pytest.param("0.00:18:50", 1130.0, id="with leading days"),
        pytest.param("01:20:30", 4830.0, id="without days"),
        pytest.param(
            "1.02:03:04.5000000", (26 * 3600) + (3 * 60) + 4, id="with fractional seconds"
        ),
        pytest.param("garbage", None, id="unparsable"),
    ],
)
def test_parse_dotnet_timespan_seconds(duration: str, expected_seconds: float | None) -> None:
    assert parse_dotnet_timespan_seconds(duration) == expected_seconds

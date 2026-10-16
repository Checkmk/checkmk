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
    CheckParameters,
    DEFAULT_DISCOVERY_PARAMETERS,
    DEFAULT_PARAMETERS,
    discovery_veeam_backup_jobs,
    DiscoveryParams,
    monitoring_state,
    parse_veeam_backup_jobs,
)
from cmk.plugins.veeam.lib import parse_iso8601_epoch

LAST_RUN = "2019-01-21T00:10:22.473+03:00"
NOW = datetime.fromisoformat(LAST_RUN).timestamp() + 3600
PARAMS = DEFAULT_PARAMETERS


def _job(
    name: str,
    session_progress: dict[str, object] | None | bool = False,
    **overrides: object,
) -> str:
    job_dict = {
        "name": name,
        "type": "Backup",
        "status": "Inactive",
        "lastRun": LAST_RUN,
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
    assert list(discovery_veeam_backup_jobs(DEFAULT_DISCOVERY_PARAMETERS, section)) == [
        Service(item="VMware_Server"),
        Service(item="warning_backup"),
        Service(item="backup_sync_job"),
        Service(item="never_run"),
        Service(item="stopped_and_failed"),
        Service(item="unknown_type"),
    ]


def test_disabled_backup_jobs_are_not_discovered_when_configured() -> None:
    section = parse_veeam_backup_jobs([[_job("enabled")], [_job("disabled", status="Disabled")]])
    params = DiscoveryParams(discover_disabled=False)

    assert list(discovery_veeam_backup_jobs(params, section)) == [Service(item="enabled")]


def test_disabled_backup_jobs_are_discovered_by_default() -> None:
    section = parse_veeam_backup_jobs([[_job("disabled", status="Disabled")]])

    assert list(discovery_veeam_backup_jobs(DEFAULT_DISCOVERY_PARAMETERS, section)) == [
        Service(item="disabled")
    ]


def test_discovered_item_is_the_sanitized_job_name() -> None:
    section = parse_veeam_backup_jobs([[_job("Bob's nightly VMs")]])

    assert list(discovery_veeam_backup_jobs(DEFAULT_DISCOVERY_PARAMETERS, section)) == [
        Service(item="Bob_s_nightly_VMs")
    ]


def test_check_veeam_backup_jobs_success() -> None:
    section = parse_veeam_backup_jobs(STRING_TABLE)
    next_run_epoch = parse_iso8601_epoch("2019-01-22T00:10:00.000+03:00")
    assert next_run_epoch is not None
    last_run = render.datetime(datetime.fromisoformat(LAST_RUN).timestamp())
    next_run = render.datetime(next_run_epoch)
    assert list(check_veeam_backup_jobs("VMware_Server", PARAMS, section, now=NOW)) == [
        Result(state=State.OK, summary="Result: Success"),
        Result(state=State.OK, summary="Time since last run: 1 hour 0 minutes"),
        Metric("veeam_backup_job_age", 3600.0),
        Result(state=State.OK, notice=f"Last run time: {last_run}"),
        Result(state=State.OK, notice="Status: Inactive"),
        Result(state=State.OK, notice="Duration: 18 minutes 50 seconds"),
        Metric("backup_duration", 1130.0),
        Result(state=State.OK, notice=f"Next run: {next_run}"),
        Result(state=State.OK, notice="Target repository: Default Backup Repository"),
        Result(state=State.OK, notice="Objects: 4"),
        Metric("veeam_backup_job_objects", 4),
        Result(state=State.OK, notice="Type: Backup"),
    ]


def test_parse_veeam_backup_jobs_unparsable_duration_becomes_none() -> None:
    section = parse_veeam_backup_jobs(
        [[_job("odd_duration", session_progress={"duration": "not-a-timespan"})]]
    )
    assert section["odd_duration"].duration is None


def test_check_veeam_backup_jobs_no_session_progress_omits_duration() -> None:
    section = parse_veeam_backup_jobs([[_job("no_progress", session_progress=None)]])
    results = list(check_veeam_backup_jobs("no_progress", PARAMS, section, now=NOW))
    assert not any("Duration" in r.details for r in results if isinstance(r, Result))


def test_check_veeam_backup_jobs_warning() -> None:
    section = parse_veeam_backup_jobs(STRING_TABLE)
    results = list(check_veeam_backup_jobs("warning_backup", PARAMS, section, now=NOW))
    assert results[0] == Result(state=State.WARN, summary="Result: Warning")


def test_check_veeam_backup_jobs_failed() -> None:
    section = parse_veeam_backup_jobs(STRING_TABLE)
    results = list(check_veeam_backup_jobs("stopped_and_failed", PARAMS, section, now=NOW))
    assert results[0] == Result(state=State.CRIT, summary="Result: Failed")


def test_check_veeam_backup_jobs_disabled_and_failed_is_ok() -> None:
    section = parse_veeam_backup_jobs([[_job("disabled", status="Disabled", lastResult="Failed")]])
    results = list(check_veeam_backup_jobs("disabled", PARAMS, section, now=NOW))
    assert results[0] == Result(state=State.OK, summary="Status: Disabled, Result: Failed")


def test_check_veeam_backup_jobs_disabled_never_run() -> None:
    section = parse_veeam_backup_jobs(
        [[_job("disabled", status="Disabled", lastRun=None, lastResult="None")]]
    )
    results = list(check_veeam_backup_jobs("disabled", PARAMS, section, now=NOW))
    assert results[0] == Result(state=State.OK, summary="Status: Disabled, No run has happened yet")


@pytest.mark.parametrize(
    "last_run, summary",
    [
        pytest.param(LAST_RUN, "Status: Disabled, Result: Failed", id="has run"),
        pytest.param(None, "Status: Disabled, No run has happened yet", id="never run"),
    ],
)
def test_check_veeam_backup_jobs_disabled_takes_the_configured_state(
    last_run: str | None,
    summary: str,
) -> None:
    section = parse_veeam_backup_jobs(
        [[_job("disabled", status="Disabled", lastRun=last_run, lastResult="Failed")]]
    )
    params = CheckParameters(disabled_state=State.WARN.value, age=("no_levels", None))
    results = list(check_veeam_backup_jobs("disabled", params, section, now=NOW))
    assert results[0] == Result(state=State.WARN, summary=summary)


@pytest.mark.parametrize(
    "status, expected",
    [
        pytest.param(
            "Inactive",
            Result(
                state=State.WARN,
                summary=(
                    "Time since last run: 1 hour 0 minutes "
                    "(warn/crit at 30 minutes 0 seconds/2 hours 0 minutes)"
                ),
            ),
            id="enabled",
        ),
        pytest.param(
            "Disabled",
            Result(state=State.OK, summary="Time since last run: 1 hour 0 minutes"),
            id="disabled",
        ),
    ],
)
def test_check_veeam_backup_jobs_age_levels_skip_disabled_jobs(
    status: str, expected: Result
) -> None:
    section = parse_veeam_backup_jobs([[_job("job", status=status)]])
    params = CheckParameters(disabled_state=State.OK.value, age=("fixed", (1800.0, 7200.0)))
    assert expected in check_veeam_backup_jobs("job", params, section, now=NOW)


def test_check_veeam_backup_jobs_never_run() -> None:
    section = parse_veeam_backup_jobs(STRING_TABLE)
    results = list(check_veeam_backup_jobs("never_run", PARAMS, section, now=NOW))
    assert results[0] == Result(state=State.OK, summary="No run has happened yet")
    next_run_epoch = parse_iso8601_epoch("2019-01-22T00:10:00.000+03:00")
    assert next_run_epoch is not None
    assert Result(state=State.OK, notice=f"Next run: {render.datetime(next_run_epoch)}") in results


def test_check_veeam_backup_jobs_unknown_type_still_renders() -> None:
    section = parse_veeam_backup_jobs(STRING_TABLE)
    results = list(check_veeam_backup_jobs("unknown_type", PARAMS, section, now=NOW))
    assert Result(state=State.OK, notice="Type: Unknown") in results


def test_check_veeam_backup_jobs_running_with_no_result_is_ok() -> None:
    section = parse_veeam_backup_jobs(STRING_TABLE)
    results = list(check_veeam_backup_jobs("backup_sync_job", PARAMS, section, now=NOW))
    assert results[0] == Result(state=State.OK, summary="Status: Running, Result: None")


@pytest.mark.parametrize(
    "previous_result, expected",
    [
        pytest.param("Success", State.OK, id="previous run succeeded"),
        pytest.param("Failed", State.CRIT, id="previous run failed"),
    ],
)
def test_running_job_keeps_the_result_of_its_previous_run(
    previous_result: str, expected: State
) -> None:
    section = parse_veeam_backup_jobs(
        [[_job("running", status="Running", lastResult=previous_result)]]
    )
    results = list(check_veeam_backup_jobs("running", PARAMS, section, now=NOW))
    assert results[0] == Result(
        state=expected, summary=f"Status: Running, Result: {previous_result}"
    )


def test_check_veeam_backup_jobs_last_run_in_the_future() -> None:
    section = parse_veeam_backup_jobs([[_job("job")]])
    now = datetime.fromisoformat(LAST_RUN).timestamp() - 60
    results = list(check_veeam_backup_jobs("job", PARAMS, section, now=now))
    assert Result(state=State.OK, summary="Last run: in the future") in results
    assert not any(isinstance(r, Metric) and r.name == "veeam_backup_job_age" for r in results)


def test_check_veeam_backup_jobs_vanished_job_goes_stale() -> None:
    section = parse_veeam_backup_jobs(STRING_TABLE)
    assert list(check_veeam_backup_jobs("no_longer_reported", PARAMS, section, now=NOW)) == []


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


def test_file_backup_job_from_vbr_13_is_monitored() -> None:
    line = (
        '{"type": "FileBackup", "status": "Stopped", "lastResult": "Success", "workload": "File",'
        ' "id": "7a597775-1100-4f22-8c74-24eae6da8921", "name": "File Backup Job 1",'
        ' "lastRun": "2026-10-02T10:50:13.688321+00:00", "nextRun": "2026-10-05T23:00:00+00:00",'
        ' "repositoryName": "Default Backup Repository", "objectsCount": 1,'
        ' "sessionProgress": {"bottleneck": "Source", "duration": "00:00:33",'
        ' "processingRate": "N/A", "processedSize": 0, "progressPercent": 100}}'
    )
    section = parse_veeam_backup_jobs([[line]])

    results = list(check_veeam_backup_jobs("File_Backup_Job_1", PARAMS, section, now=NOW))

    assert results[0] == Result(state=State.OK, summary="Result: Success")
    assert Result(state=State.OK, notice="Type: FileBackup") in results

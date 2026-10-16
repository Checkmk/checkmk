#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Result, Service, State
from cmk.plugins.veeam.agent_based.veeam_jobs import (
    check_veeam_jobs,
    discovery_veeam_jobs,
    Job,
    monitoring_state,
    parse_veeam_agent_policy_workloads,
    parse_veeam_jobs,
    PolicyWorkloads,
    Workload,
)

STRING_TABLE = [
    [  # based on customer agent output, this is the most common state
        "VMware_Server",
        "Backup",
        "Stopped",
        "Success",
        "21.01.2019 00:10:22",
        "21.01.2019 00:29:12",
    ],
    [  # based on customer agent output
        "warning_backup",
        "Backup",
        "Stopped",
        "Warning",
        "03.09.2020 15:45:50",
        "03.09.2020 16:44:39",
    ],
    [  # based on customer agent output
        "backup_sync_job",
        "BackupSync",
        "Working",
        "None",
        "20.07.2017 08:25:09",
        "20.07.2017 08:25:29",
    ],
    [  # based on customer agent output, happens if creation time/end time are empty
        "backup_stopped",
        "Backup",
        "Stopped",
        "None",
    ],
    [  # based on customer agent output
        "stopped_and_failed",
        "Backup",
        "Stopped",
        "Failed",
        "26.10.2013 23:13:13",
        "27.10.2013 00:51:17",
    ],
    [  # based on customer agent output
        "starting_and_failed",
        "Backup",
        "Starting",
        "Failed",
        "26.10.2013 23:13:13",
        "27.10.2013 00:51:17",
    ],
    ["Lehrer Rechner"],
    [  # made up to get 100% coverage of check,
        "backup_sync_idle",
        "BackupSync",
        "Idle",
        "None",
        "20.07.2017 08:25:09",
        "20.07.2017 08:25:29",
    ],
]


def test_discovery_veeam_jobs() -> None:
    section = parse_veeam_jobs(STRING_TABLE)
    assert list(discovery_veeam_jobs(section, None)) == [
        Service(item="VMware_Server"),
        Service(item="warning_backup"),
        Service(item="backup_sync_job"),
        Service(item="backup_stopped"),
        Service(item="stopped_and_failed"),
        Service(item="starting_and_failed"),
        Service(item="Lehrer Rechner"),
        Service(item="backup_sync_idle"),
    ]


def test_check_veeam_jobs() -> None:
    section = parse_veeam_jobs(STRING_TABLE)
    items = [
        service.item or ""
        for service in discovery_veeam_jobs(section, None)
        if service.item != "backup_sync_job"
    ]

    results = [(item, list(check_veeam_jobs(item, section, None))) for item in items]
    assert results == [
        (
            "VMware_Server",
            [
                Result(state=State.OK, summary="State: Stopped, Result: Success"),
                Result(state=State.OK, summary="Creation time: 21.01.2019 00:10:22"),
                Result(state=State.OK, summary="End time: 21.01.2019 00:29:12"),
                Result(state=State.OK, summary="Type: Backup"),
            ],
        ),
        (
            "warning_backup",
            [
                Result(state=State.WARN, summary="State: Stopped, Result: Warning"),
                Result(state=State.OK, summary="Creation time: 03.09.2020 15:45:50"),
                Result(state=State.OK, summary="End time: 03.09.2020 16:44:39"),
                Result(state=State.OK, summary="Type: Backup"),
            ],
        ),
        (
            "backup_stopped",
            [
                Result(state=State.OK, summary="State: Stopped, Result: None"),
                Result(state=State.OK, summary="Type: Backup"),
            ],
        ),
        (
            "stopped_and_failed",
            [
                Result(state=State.CRIT, summary="State: Stopped, Result: Failed"),
                Result(state=State.OK, summary="Creation time: 26.10.2013 23:13:13"),
                Result(state=State.OK, summary="End time: 27.10.2013 00:51:17"),
                Result(state=State.OK, summary="Type: Backup"),
            ],
        ),
        (
            "starting_and_failed",
            [
                Result(state=State.CRIT, summary="State: Starting, Result: Failed"),
                Result(state=State.OK, summary="Creation time: 26.10.2013 23:13:13"),
                Result(state=State.OK, summary="End time: 27.10.2013 00:51:17"),
                Result(state=State.OK, summary="Type: Backup"),
            ],
        ),
        ("Lehrer Rechner", []),
        (
            "backup_sync_idle",
            [
                Result(state=State.OK, summary="State: Idle, Result: None"),
                Result(state=State.OK, summary="Creation time: 20.07.2017 08:25:09"),
                Result(state=State.OK, summary="End time: 20.07.2017 08:25:29"),
                Result(state=State.OK, summary="Type: BackupSync"),
            ],
        ),
    ]


def test_check_veeam_jobs_running_raises_ignore_results() -> None:
    section = parse_veeam_jobs(STRING_TABLE)
    with pytest.raises(IgnoreResultsError):
        list(check_veeam_jobs("backup_sync_job", section, None))


def test_parse_veeam_jobs_pads_missing_trailing_columns() -> None:
    # A job that has never run has no last session, so the agent sends empty
    # creation and end times and the trailing tab separators are dropped.
    assert parse_veeam_jobs([["backup_stopped", "Backup", "Stopped", "None"]]) == {
        "backup_stopped": Job(
            type_="Backup",
            last_state="Stopped",
            last_result="None",
            creation_time="",
            end_time="",
        )
    }


def test_parse_veeam_jobs_job_without_data() -> None:
    assert parse_veeam_jobs([["Lehrer Rechner"]]) == {"Lehrer Rechner": None}


@pytest.mark.parametrize(
    "last_state, last_result, expected",
    [
        pytest.param("Stopped", "Success", State.OK, id="succeeded"),
        pytest.param("Stopped", "Warning", State.WARN, id="finished with warning"),
        pytest.param("Stopped", "Failed", State.CRIT, id="failed"),
        pytest.param("Stopped", "Kaputt", State.UNKNOWN, id="unparsable result"),
        pytest.param("Stopped", "None", State.OK, id="never executed"),
        pytest.param("Idle", "None", State.OK, id="idle without result"),
        pytest.param("Suspended", "None", State.OK, id="suspended without result"),
        pytest.param("Levitating", "None", State.UNKNOWN, id="unparsable state"),
    ],
)
def test_monitoring_state(last_state: str, last_result: str, expected: State) -> None:
    assert monitoring_state(last_state, last_result) == expected


@pytest.mark.parametrize("last_state", ["Starting", "Working", "Postprocessing"])
def test_monitoring_state_running_raises_ignore_results(last_state: str) -> None:
    with pytest.raises(IgnoreResultsError):
        monitoring_state(last_state, "None")


POLICY_JOBS = parse_veeam_jobs(
    [["Policy_Wave_1", "EpAgentPolicy", "Stopped", "Success", "26.08.2026 15:47:13"]]
)
POLICY_RESULTS = [
    Result(state=State.OK, summary="State: Stopped, Result: Success"),
    Result(state=State.OK, summary="Creation time: 26.08.2026 15:47:13"),
    Result(state=State.OK, summary="Type: EpAgentPolicy"),
]


def _check_policy(*workloads: tuple[str, str]) -> list[object]:
    section = parse_veeam_agent_policy_workloads(
        [
            [
                "computer",
                "Policy_Wave_1",
                name,
                "Stopped",
                result,
                "26.08.2026 15:47:13",
                "26.08.2026 15:50:00",
            ]
            for name, result in workloads
        ]
    )
    return list(check_veeam_jobs("Policy_Wave_1", POLICY_JOBS, section))


@pytest.mark.parametrize(
    "result, state",
    [
        pytest.param("Warning", State.WARN, id="warning"),
        pytest.param("Failed", State.CRIT, id="failed"),
    ],
)
def test_unhealthy_workload_is_not_masked_by_policy_result(result: str, state: State) -> None:
    assert _check_policy(("SRV-DC01", result), ("SRV-APP01", "Success")) == [
        *POLICY_RESULTS,
        Result(state=state, summary=f"SRV-DC01: {result} (ended 26.08.2026 15:50:00)"),
        Result(
            state=State.OK,
            notice="Protected computers without problems: 1",
            details="SRV-APP01: Success (ended 26.08.2026 15:50:00)",
        ),
    ]


def test_many_unhealthy_workloads_are_counted() -> None:
    assert _check_policy(*((f"PC{i}", "Failed") for i in range(4))) == [
        *POLICY_RESULTS,
        Result(
            state=State.CRIT,
            summary="Protected computers with failed backups: 4",
            details="\n".join(f"PC{i}: Failed (ended 26.08.2026 15:50:00)" for i in range(4)),
        ),
    ]


def test_running_workload_is_not_reported() -> None:
    section = parse_veeam_agent_policy_workloads(
        [["computer", "Policy_Wave_1", "SRV-DC01", "Working", "None", "26.08.2026 15:47:13"]]
    )
    assert list(check_veeam_jobs("Policy_Wave_1", POLICY_JOBS, section)) == POLICY_RESULTS


def test_workload_without_finished_backup_is_listed() -> None:
    section = parse_veeam_agent_policy_workloads(
        [["computer", "Policy_Wave_1", "SRV-NEW", "None", "None"]]
    )
    assert list(check_veeam_jobs("Policy_Wave_1", POLICY_JOBS, section)) == [
        *POLICY_RESULTS,
        Result(
            state=State.OK,
            notice="Protected computers without a finished backup yet: 1",
            details="SRV-NEW",
        ),
    ]


@pytest.mark.parametrize("policy", ["Policy_Wave_1", "*"])
def test_failure_to_determine_workloads_is_unknown(policy: str) -> None:
    section = parse_veeam_agent_policy_workloads([["error", policy, "Access", "denied"]])
    assert list(check_veeam_jobs("Policy_Wave_1", POLICY_JOBS, section)) == [
        *POLICY_RESULTS,
        Result(
            state=State.UNKNOWN,
            summary="Could not determine the protected computers: Access denied",
        ),
    ]


def test_failure_for_all_policies_does_not_affect_other_jobs() -> None:
    jobs = parse_veeam_jobs([["Backup_Job", "Backup", "Stopped", "Success"]])
    section = parse_veeam_agent_policy_workloads([["error", "*", "Access denied"]])
    assert list(check_veeam_jobs("Backup_Job", jobs, section)) == [
        Result(state=State.OK, summary="State: Stopped, Result: Success"),
        Result(state=State.OK, summary="Type: Backup"),
    ]


def test_policy_without_workload_section_is_unchanged() -> None:
    assert list(check_veeam_jobs("Policy_Wave_1", POLICY_JOBS, None)) == POLICY_RESULTS


def test_parse_veeam_agent_policy_workloads() -> None:
    assert parse_veeam_agent_policy_workloads(
        [
            ["computer", "Policy_Wave_1", "SRV-DC01", "Stopped", "Warning", "26.08.2026 15:47:13"],
            ["error", "Policy_Wave_2", "Access denied"],
            ["broken"],
        ]
    ) == {
        "Policy_Wave_1": PolicyWorkloads(
            workloads=[
                Workload(
                    name="SRV-DC01",
                    last_state="Stopped",
                    last_result="Warning",
                    creation_time="26.08.2026 15:47:13",
                    end_time="",
                )
            ],
            error=None,
        ),
        "Policy_Wave_2": PolicyWorkloads(workloads=[], error="Access denied"),
    }

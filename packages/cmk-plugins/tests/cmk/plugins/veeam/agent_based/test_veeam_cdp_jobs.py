#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import (
    DiscoveryResult,
    IgnoreResults,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.veeam.agent_based import veeam_cdp_jobs

NOW = 1787847600
SESSION_END = NOW - 3600
PARAMS = veeam_cdp_jobs.CheckParams(age=("fixed", (60.0, 120.0)))


def _check(line: list[str]) -> list[IgnoreResults | Metric | Result]:
    section = veeam_cdp_jobs.parse_veeam_cdp_jobs([line])
    return list(veeam_cdp_jobs.check_veeam_cdp_jobs_at(line[0], PARAMS, section, NOW))


def test_discovery() -> None:
    string_table: StringTable = [
        ["Job 1", "null", "Running"],
        ["Job 2", "null", "Running", "null", "null"],
        ["Job 3", "null", "Running", "null", "null", "null"],
    ]
    expected: DiscoveryResult = [
        Service(item="Job 1"),
        Service(item="Job 2"),
        Service(item="Job 3"),
    ]
    section = veeam_cdp_jobs.parse_veeam_cdp_jobs(string_table)
    params = veeam_cdp_jobs.DEFAULT_DISCOVERY_PARAMETERS
    assert list(veeam_cdp_jobs.discovery_veeam_cdp_jobs(params, section)) == expected


def test_disabled_cdp_jobs_are_not_discovered_when_configured() -> None:
    section = veeam_cdp_jobs.parse_veeam_cdp_jobs(
        [["Job 1", "null", "Running"], ["Job 2", "null", "Disabled", "null", "null"]]
    )
    params = veeam_cdp_jobs.DiscoveryParams(discover_disabled=False)

    assert list(veeam_cdp_jobs.discovery_veeam_cdp_jobs(params, section)) == [Service(item="Job 1")]


def test_recent_restore_point_and_successful_session() -> None:
    assert _check(["Job", "null", "Running", str(NOW - 30), "Success", str(SESSION_END)]) == [
        Result(state=State.OK, summary="State: Running"),
        Result(
            state=State.OK,
            summary=f"Last session: Success, ended {render.datetime(SESSION_END)}",
        ),
        Result(state=State.OK, summary="Time since last long-term restore point: 30 seconds"),
    ]


@pytest.mark.parametrize(
    "age, expected",
    [
        pytest.param(
            90,
            Result(
                state=State.WARN,
                summary="Time since last long-term restore point: 1 minute 30 seconds (warn/crit at 1 minute 0 seconds/2 minutes 0 seconds)",
            ),
            id="warn",
        ),
        pytest.param(
            150,
            Result(
                state=State.CRIT,
                summary="Time since last long-term restore point: 2 minutes 30 seconds (warn/crit at 1 minute 0 seconds/2 minutes 0 seconds)",
            ),
            id="crit",
        ),
    ],
)
def test_restore_point_age_levels(age: int, expected: Result) -> None:
    assert _check(["Job", "null", "Running", str(NOW - age), "null", "null"])[-1] == expected


def test_restore_point_in_the_future_warns() -> None:
    assert _check(["Job", "null", "Running", str(NOW + 60), "null", "null"])[-1] == Result(
        state=State.WARN,
        summary=(
            "The last long-term restore point is in the future. "
            "Please check the clocks of the Veeam server and the Checkmk server."
        ),
    )


@pytest.mark.parametrize(
    "last_result, state",
    [("Success", State.OK), ("Warning", State.WARN), ("Failed", State.CRIT)],
)
def test_last_session_result(last_result: str, state: State) -> None:
    assert _check(["Job", "null", "Running", "null", last_result, "null"]) == [
        Result(state=State.OK, summary="State: Running"),
        Result(state=state, summary=f"Last session: {last_result}"),
    ]


def test_unmodelled_last_session_result_is_unknown() -> None:
    assert _check(["Job", "null", "Running", "null", "Running", "null"]) == [
        Result(state=State.OK, summary="State: Running"),
        Result(state=State.UNKNOWN, summary="Last session: Running"),
    ]


def test_disabled_policy_is_not_age_checked() -> None:
    assert _check(["Job", "null", "Disabled", str(NOW - 365 * 86400), "Success", "null"]) == [
        Result(state=State.OK, summary="State: Disabled"),
        Result(state=State.OK, notice="Last session: Success"),
    ]


def test_failed_last_session_of_disabled_policy_is_only_a_notice() -> None:
    assert _check(["Job", "null", "Disabled", "null", "Failed", "null"]) == [
        Result(state=State.OK, summary="State: Disabled"),
        Result(state=State.OK, notice="Last session: Failed"),
    ]


def test_initial_sync_is_ok() -> None:
    assert _check(["Job", "null", "InitialSync", "null", "null", "null"]) == [
        Result(state=State.OK, summary="State: InitialSync"),
    ]


def test_policy_result_of_previous_agent_plugin_is_ignored() -> None:
    assert _check(["Job", "1787847691", "Running", "null", "Failed"]) == [
        Result(state=State.OK, summary="State: Running"),
    ]


def test_old_agent_output_reports_only_the_state() -> None:
    assert _check(["Job", "1787847691,39556", "Running"]) == [
        Result(state=State.OK, summary="State: Running"),
    ]


def test_unmodelled_policy_state_is_reported_as_unknown() -> None:
    assert _check(["Job", "null", "Starting"]) == [
        Result(state=State.UNKNOWN, summary="State: Starting")
    ]


def test_line_with_unexpected_field_count_is_skipped() -> None:
    section = veeam_cdp_jobs.parse_veeam_cdp_jobs(
        [["Job 1", "null"], ["Job 2", "null", "Running", "null"], ["Job 3", "null", "Running"]]
    )

    params = veeam_cdp_jobs.DEFAULT_DISCOVERY_PARAMETERS
    assert list(veeam_cdp_jobs.discovery_veeam_cdp_jobs(params, section)) == [Service(item="Job 3")]


def test_unparseable_timestamps_are_omitted() -> None:
    assert _check(["Job", "null", "Running", "garbage", "null", "garbage"]) == [
        Result(state=State.OK, summary="State: Running")
    ]

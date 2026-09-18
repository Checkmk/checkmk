#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Sequence
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.veeam.agent_based.veeam_client import (
    check_veeam_client,
    discover_veeam_client,
    parse_veeam_client,
)


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param(
            [
                ["Status", "Success"],
                ["JobName", "JOB_NAME"],
                ["TotalSizeByte", "100"],
                ["StartTime", "01.02.2015 20:05:45"],
                ["StopTime", "01.02.2015 21:05:45"],
                ["DurationDDHHMMSS", "00:01:00:00"],
                ["AvgSpeedBps", "100"],
                ["DisplayName", "name"],
            ],
            [Service(item="JOB_NAME")],
            id="section with status",
        ),
    ],
)
def test_discover_veeam_client(
    string_table: StringTable, expected_result: Sequence[Service]
) -> None:
    assert list(discover_veeam_client(parse_veeam_client(string_table))) == expected_result


@pytest.mark.parametrize(
    "item, string_table, expected_summary, expected_state",
    [
        pytest.param(
            "JOB_NAME",
            [
                ["Status", "Success"],
                ["JobName", "JOB_NAME"],
                ["TotalSizeByte", "100"],
                ["StartTime", "01.02.2015 20:05:45"],
                ["DurationDDHHMMSS", "00:01:00:00"],
                ["AvgSpeedBps", "100"],
                ["DisplayName", "name"],
            ],
            "Status: Success, Size (total): 100 B, No complete Backup(!!), Duration: 1 "
            "hour 0 minutes, Average Speed: 100 B/s",
            State.CRIT,
            id="section without StopTime or LastBackupAge",
        ),
        pytest.param(
            "JOB_NAME",
            [
                ["Status", "Success"],
                ["JobName", "JOB_NAME"],
                ["TotalSizeByte", "100"],
                ["StartTime", "01.02.2015 20:05:45"],
                ["LastBackupAge", "5"],
                ["DurationDDHHMMSS", "00:01:00:00"],
                ["AvgSpeedBps", "100"],
                ["DisplayName", "name"],
            ],
            "Status: Success, Size (total): 100 B, Last backup: 5 seconds ago, Duration: "
            "1 hour 0 minutes, Average Speed: 100 B/s",
            State.OK,
            id="section success LastBackupAge",
        ),
        pytest.param(
            "JOB_NAME",
            [
                ["Status", "InProgress"],
                ["JobName", "JOB_NAME"],
                ["TotalSizeByte", "100"],
                ["StartTime", "01.02.2015 20:05:45"],
                ["StopTime", "01.02.2015 21:00:50"],
                ["DurationDDHHMMSS", "00:01:00:00"],
                ["AvgSpeedBps", "100"],
                ["DisplayName", "name"],
            ],
            "Status: InProgress, Size (total): 100 B, Average Speed: 100 B/s",
            State.OK,
            id="section in progress StopTime",
        ),
        pytest.param(
            "JOB_NAME",
            [
                ["Status", "InProgress"],
                ["JobName", "JOB_NAME"],
                ["TotalSizeByte", "100"],
                ["StartTime", "01.02.2015 20:05:45"],
                ["LastBackupAge", "300"],
                ["DurationDDHHMMSS", "00:01:00:00"],
                ["AvgSpeedBps", "100"],
                ["DisplayName", "name"],
            ],
            "Status: InProgress, Size (total): 100 B, Average Speed: 100 B/s",
            State.OK,
            id="section in progress LastBackupAge",
        ),
    ],
)
def test_check_veeam_client(
    item: str,
    string_table: StringTable,
    expected_summary: str,
    expected_state: State,
) -> None:
    with time_machine.travel(
        datetime.datetime.fromisoformat("2015-02-01 21:05:50").replace(tzinfo=ZoneInfo("CET")),
        tick=False,
    ):
        results = list(
            check_veeam_client(
                item, params={"age": (20, 40)}, section=parse_veeam_client(string_table)
            )
        )
        result_obj = [r for r in results if isinstance(r, Result)][0]
        assert result_obj.state == expected_state
        assert result_obj.summary == expected_summary


def _check_results(string_table: StringTable) -> list[Result]:
    return [
        result
        for result in check_veeam_client(
            "JOB_NAME", params={"age": (20, 40)}, section=parse_veeam_client(string_table)
        )
        if isinstance(result, Result)
    ]


@pytest.mark.parametrize(
    "size_lines",
    [
        pytest.param([], id="field absent"),
        pytest.param([["TotalSizeByte", ""]], id="field empty"),
    ],
)
def test_unreported_total_size_is_omitted_from_the_summary(size_lines: StringTable) -> None:
    results = _check_results(
        [
            ["Status", "Success"],
            ["JobName", "JOB_NAME"],
            *size_lines,
            ["LastBackupAge", "5"],
        ]
    )

    assert results == [
        Result(state=State.OK, summary="Status: Success, Last backup: 5 seconds ago")
    ]


def test_unparseable_stop_time_reports_no_complete_backup() -> None:
    results = _check_results(
        [
            ["Status", "Success"],
            ["JobName", "JOB_NAME"],
            ["TotalSizeByte", "100"],
            ["StopTime", "not a date"],
        ]
    )

    assert results == [
        Result(
            state=State.CRIT,
            summary="Status: Success, Size (total): 100 B, No complete Backup(!!)",
        )
    ]


def test_malformed_duration_is_omitted_from_the_summary() -> None:
    results = _check_results(
        [
            ["Status", "Success"],
            ["JobName", "JOB_NAME"],
            ["LastBackupAge", "5"],
            ["DurationDDHHMMSS", "00:01:00"],
        ]
    )

    assert results == [
        Result(state=State.OK, summary="Status: Success, Last backup: 5 seconds ago")
    ]


# The following tests pin the current behaviour of the age levels and the status
# mapping. They are characterization tests: the hand-rolled "(!)"/"(!!)" markers
# and the "(Warn/Crit: ...)" text are exactly today's output, and are expected to
# change when the check moves to check_levels. Levels are compared inclusively
# (age >= warn / age >= crit), so the boundary values are pinned as well.


@pytest.mark.parametrize(
    "last_backup_age, expected_result",
    [
        pytest.param(
            "20",
            Result(
                state=State.WARN,
                summary="Status: Success, Last backup: 20 seconds ago(!) "
                "(Warn/Crit: 20 seconds/40 seconds)",
            ),
            id="age equal to the warn level",
        ),
        pytest.param(
            "30",
            Result(
                state=State.WARN,
                summary="Status: Success, Last backup: 30 seconds ago(!) "
                "(Warn/Crit: 20 seconds/40 seconds)",
            ),
            id="age inside the warn band",
        ),
        pytest.param(
            "40",
            Result(
                state=State.CRIT,
                summary="Status: Success, Last backup: 40 seconds ago(!!) "
                "(Warn/Crit: 20 seconds/40 seconds)",
            ),
            id="age equal to the crit level",
        ),
        pytest.param(
            "50",
            Result(
                state=State.CRIT,
                summary="Status: Success, Last backup: 50 seconds ago(!!) "
                "(Warn/Crit: 20 seconds/40 seconds)",
            ),
            id="age above the crit level",
        ),
    ],
)
def test_last_backup_age_levels(last_backup_age: str, expected_result: Result) -> None:
    results = _check_results(
        [["Status", "Success"], ["JobName", "JOB_NAME"], ["LastBackupAge", last_backup_age]]
    )

    assert results == [expected_result]


@pytest.mark.parametrize(
    "status, expected_state",
    [
        pytest.param("Warning", State.WARN, id="status Warning is a warning"),
        pytest.param("Failed", State.CRIT, id="status Failed is critical"),
    ],
)
def test_status_maps_to_the_service_state(status: str, expected_state: State) -> None:
    results = _check_results([["Status", status], ["JobName", "JOB_NAME"], ["LastBackupAge", "5"]])

    assert results == [
        Result(state=expected_state, summary=f"Status: {status}, Last backup: 5 seconds ago")
    ]


def _stop_time_results(stop_time: str) -> list[Result]:
    # time_machine.travel pins $TZ from the ZoneInfo, so the mktime the StopTime
    # fallback uses is deterministic. CET matches the rest of the module.
    with time_machine.travel(
        datetime.datetime(2015, 2, 1, 21, 5, 50, tzinfo=ZoneInfo("CET")), tick=False
    ):
        return _check_results(
            [["Status", "Success"], ["JobName", "JOB_NAME"], ["StopTime", stop_time]]
        )


@pytest.mark.parametrize(
    "stop_time, expected_result",
    [
        pytest.param(
            "01.02.2015 21:05:20",
            Result(
                state=State.WARN,
                summary="Status: Success, Last backup: 30 seconds ago(!) "
                "(Warn/Crit: 20 seconds/40 seconds)",
            ),
            id="stop time above the warn level",
        ),
        pytest.param(
            "01.02.2015 21:05:00",
            Result(
                state=State.CRIT,
                summary="Status: Success, Last backup: 50 seconds ago(!!) "
                "(Warn/Crit: 20 seconds/40 seconds)",
            ),
            id="stop time above the crit level",
        ),
        pytest.param(
            "01.01.1900 00:00:00",
            Result(state=State.OK, summary="Status: Success"),
            id="running backup sentinel omits the age",
        ),
    ],
)
def test_stop_time_fallback(stop_time: str, expected_result: Result) -> None:
    assert _stop_time_results(stop_time) == [expected_result]

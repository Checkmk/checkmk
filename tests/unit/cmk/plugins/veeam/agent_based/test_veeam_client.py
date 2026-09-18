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

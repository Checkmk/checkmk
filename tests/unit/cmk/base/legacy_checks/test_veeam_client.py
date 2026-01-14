#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import datetime
from collections.abc import Mapping, Sequence
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.veeam_client import (
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
            [("JOB_NAME", {})],
            id="section with status",
        ),
    ],
)
def test_discover_veeam_client(
    string_table: StringTable, expected_result: Sequence[tuple[str, Mapping[str, object]]]
) -> None:
    assert list(discover_veeam_client(parse_veeam_client(string_table))) == expected_result


@pytest.mark.parametrize(
    "item, string_table, expected_result",
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
            [
                2,
                "Status: Success, Size (total): 100 B, No complete Backup(!!), Duration: 1 "
                "hour 0 minutes, Average Speed: 100 B/s",
                [("totalsize", 100), ("duration", 3600), ("avgspeed", 100)],
            ],
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
            [
                0,
                "Status: Success, Size (total): 100 B, Last backup: 5 seconds ago, Duration: "
                "1 hour 0 minutes, Average Speed: 100 B/s",
                [("totalsize", 100), ("duration", 3600), ("avgspeed", 100)],
            ],
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
            [
                0,
                "Status: InProgress, Size (total): 100 B, Average Speed: 100 B/s",
                [("totalsize", 100), ("avgspeed", 100)],
            ],
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
            [
                0,
                "Status: InProgress, Size (total): 100 B, Average Speed: 100 B/s",
                [("totalsize", 100), ("avgspeed", 100)],
            ],
            id="section in progress LastBackupAge",
        ),
    ],
)
def test_check_veeam_client(
    item: str,
    string_table: StringTable,
    expected_result: Sequence[tuple[int, str, Sequence[tuple[str, int]]]],
) -> None:
    with time_machine.travel(
        datetime.datetime.fromisoformat("2015-02-01 21:05:50").replace(tzinfo=ZoneInfo("CET")),
        tick=False,
    ):
        assert (
            list(
                check_veeam_client(
                    item, params={"age": (20, 40)}, parsed=parse_veeam_client(string_table)
                )
            )
            == expected_result
        )

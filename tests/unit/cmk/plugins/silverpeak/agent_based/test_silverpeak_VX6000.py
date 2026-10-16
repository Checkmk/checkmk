#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.silverpeak.agent_based.silverpeak_VX6000 import (
    check_silverpeak,
    discover_silverpeak_VX6000,
    parse_silverpeak,
)

type InfoType = Sequence[StringTable]


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            [
                [["4"]],
                [
                    ["0", "Tunnel state is Up", "if1"],
                    ["2", "System BYPASS mode", "mysystem"],
                    ["4", "Tunnel state is Down", "to_sp01-dnd_WAN-WAN"],
                    ["8", "Disk is not in service", "mydisk"],
                ],
            ],
            [Service()],
        ),
    ],
)
def test_discover_silverpeak_VX6000(
    info: InfoType, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for silverpeak_VX6000 check."""
    parsed = parse_silverpeak(info)
    assert parsed is not None
    result = list(discover_silverpeak_VX6000(parsed))
    assert sorted(result, key=str) == sorted(expected_discoveries, key=str)


@pytest.mark.parametrize(
    "info, expected_results",
    [
        (
            [
                [["4"]],
                [
                    ["0", "Tunnel state is Up", "if1"],
                    ["2", "System BYPASS mode", "mysystem"],
                    ["4", "Tunnel state is Down", "to_sp01-dnd_WAN-WAN"],
                    ["8", "Disk is not in service", "mydisk"],
                ],
            ],
            [
                Result(
                    state=State.OK,
                    summary="4 active alarms. OK: 1, WARN: 1, CRIT: 1, UNKNOWN: 1",
                ),
                Result(
                    state=State.OK,
                    summary="Alarm: Tunnel state is Up, Alarm-Source: if1, Severity: info",
                ),
                Result(
                    state=State.WARN,
                    summary="Alarm: System BYPASS mode, Alarm-Source: mysystem, Severity: minor",
                ),
                Result(
                    state=State.CRIT,
                    summary="Alarm: Tunnel state is Down, Alarm-Source: to_sp01-dnd_WAN-WAN, Severity: critical",
                ),
                Result(
                    state=State.UNKNOWN,
                    summary="Alarm: Disk is not in service, Alarm-Source: mydisk, Severity: indeterminate",
                ),
            ],
        ),
    ],
)
def test_check_silverpeak_VX6000(info: InfoType, expected_results: Sequence[Result]) -> None:
    """Test check function for silverpeak_VX6000 check."""
    parsed = parse_silverpeak(info)
    assert parsed is not None
    result = list(check_silverpeak(parsed))
    assert result == expected_results


@pytest.mark.xfail(
    strict=True,
    raises=KeyError,
    reason="Crash report 9be3337a-c8a8-11f1-b2c1-0050568d12fe: KeyError",
)
def test_check_silverpeak_VX6000_alarm_count_without_alarm_rows() -> None:
    # Crash group 4960: the device reported three active alarms, but its alarm
    # table delivered no rows.
    parsed = parse_silverpeak([[["3"]], []])
    assert parsed is not None
    assert list(check_silverpeak(parsed)) == [
        Result(
            state=State.OK,
            summary="3 active alarms. OK: 0, WARN: 0, CRIT: 0, UNKNOWN: 0",
        ),
        Result(
            state=State.UNKNOWN,
            summary="Device reports 3 active alarms but delivered no alarm details",
        ),
    ]

#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.silverpeak_VX6000 import (
    check_silverpeak,
    discover_silverpeak_VX6000,
    parse_silverpeak,
)


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
            [(None, {})],
        ),
    ],
)
def test_discover_silverpeak_VX6000(
    info: StringTable, expected_discoveries: Sequence[tuple[str | None, Mapping[str, Any]]]
) -> None:
    """Test discovery function for silverpeak_VX6000 check."""
    parsed = parse_silverpeak(info)
    result = list(discover_silverpeak_VX6000(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            None,
            {},
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
                (0, "4 active alarms. OK: 1, WARN: 1, CRIT: 1, UNKNOWN: 1"),
                (0, "\nAlarm: Tunnel state is Up, Alarm-Source: if1, Severity: info"),
                (1, "\nAlarm: System BYPASS mode, Alarm-Source: mysystem, Severity: minor"),
                (
                    2,
                    "\nAlarm: Tunnel state is Down, Alarm-Source: to_sp01-dnd_WAN-WAN, Severity: critical",
                ),
                (
                    3,
                    "\nAlarm: Disk is not in service, Alarm-Source: mydisk, Severity: indeterminate",
                ),
            ],
        ),
    ],
)
def test_check_silverpeak_VX6000(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for silverpeak_VX6000 check."""
    parsed = parse_silverpeak(info)
    result = list(check_silverpeak(item, params, parsed))
    assert result == expected_results

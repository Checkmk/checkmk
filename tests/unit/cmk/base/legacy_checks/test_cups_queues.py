#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

import datetime
from collections.abc import Mapping, Sequence
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.cups_queues import (
    check_cups_queues,
    discover_cups_queues,
    parse_cups_queues,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    "printer",
                    "spr1",
                    "is",
                    "idle.",
                    "enabled",
                    "since",
                    "Thu",
                    "Mar",
                    "11",
                    "14:28:23",
                    "2010",
                ],
                [
                    "printer",
                    "lpr2",
                    "now",
                    "printing",
                    "lpr2-3.",
                    "enabled",
                    "since",
                    "Tue",
                    "Jun",
                    "29",
                    "09:22:04",
                    "2010",
                ],
                [
                    "Wiederherstellbar:",
                    "Der",
                    "Netzwerk-Host",
                    "lpr2",
                    "ist",
                    "beschaeftigt,",
                    "erneuter",
                    "Versuch",
                    "in",
                    "30",
                    "Sekunden",
                ],
                ["---"],
                ["lpr2-2", "root", "1024", "Tue", "Jun", "28", "09:05:56", "2010"],
                ["lpr2-3", "root", "1024", "Tue", "28", "Jun", "2010", "01:02:35", "PM", "CET"],
                ["lpr2-4", "root", "1024", "Tue", "29", "Jun", "2010", "09:05:54", "AM", "CET"],
            ],
            [("lpr2", {}), ("spr1", {})],
        ),
    ],
)
def test_discover_cups_queues(
    string_table: StringTable,
    expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]],
) -> None:
    """Test discovery function for cups_queues check."""
    with time_machine.travel(datetime.datetime.fromtimestamp(1659514516, tz=ZoneInfo("CET"))):
        parsed = parse_cups_queues(string_table)
        result = list(discover_cups_queues(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "lpr2",
            {
                "disabled_since": 2,
                "is_idle": 0,
                "job_age": (360, 720),
                "job_count": (5, 10),
                "now_printing": 0,
            },
            [
                [
                    "printer",
                    "spr1",
                    "is",
                    "idle.",
                    "enabled",
                    "since",
                    "Thu",
                    "Mar",
                    "11",
                    "14:28:23",
                    "2010",
                ],
                [
                    "printer",
                    "lpr2",
                    "now",
                    "printing",
                    "lpr2-3.",
                    "enabled",
                    "since",
                    "Tue",
                    "Jun",
                    "29",
                    "09:22:04",
                    "2010",
                ],
                [
                    "Wiederherstellbar:",
                    "Der",
                    "Netzwerk-Host",
                    "lpr2",
                    "ist",
                    "beschaeftigt,",
                    "erneuter",
                    "Versuch",
                    "in",
                    "30",
                    "Sekunden",
                ],
                ["---"],
                ["lpr2-2", "root", "1024", "Tue", "Jun", "28", "09:05:56", "2010"],
                ["lpr2-3", "root", "1024", "Tue", "28", "Jun", "2010", "01:02:35", "PM", "CET"],
                ["lpr2-4", "root", "1024", "Tue", "29", "Jun", "2010", "09:05:54", "AM", "CET"],
            ],
            [
                (
                    0,
                    "now printing lpr2-3. enabled since Tue Jun 29 09:22:04 2010 (Wiederherstellbar: Der Netzwerk-Host lpr2 ist beschaeftigt, erneuter Versuch in 30 Sekunden)",
                ),
                (0, "Jobs: 3", [("jobs", 3, 5, 10)]),
                (0, "Oldest job is from 2010-06-28 09:05:56"),
                (
                    2,
                    "Age of oldest job: 12 years 39 days (warn/crit at 6 minutes 0 "
                    "seconds/12 minutes 0 seconds)",
                    [],
                ),
            ],
        ),
        (
            "spr1",
            {
                "disabled_since": 2,
                "is_idle": 0,
                "job_age": (360, 720),
                "job_count": (5, 10),
                "now_printing": 0,
            },
            [
                [
                    "printer",
                    "spr1",
                    "is",
                    "idle.",
                    "enabled",
                    "since",
                    "Thu",
                    "Mar",
                    "11",
                    "14:28:23",
                    "2010",
                ],
                [
                    "printer",
                    "lpr2",
                    "now",
                    "printing",
                    "lpr2-3.",
                    "enabled",
                    "since",
                    "Tue",
                    "Jun",
                    "29",
                    "09:22:04",
                    "2010",
                ],
                [
                    "Wiederherstellbar:",
                    "Der",
                    "Netzwerk-Host",
                    "lpr2",
                    "ist",
                    "beschaeftigt,",
                    "erneuter",
                    "Versuch",
                    "in",
                    "30",
                    "Sekunden",
                ],
                ["---"],
                ["lpr2-2", "root", "1024", "Tue", "Jun", "28", "09:05:56", "2010"],
                ["lpr2-3", "root", "1024", "Tue", "28", "Jun", "2010", "01:02:35", "PM", "CET"],
                ["lpr2-4", "root", "1024", "Tue", "29", "Jun", "2010", "09:05:54", "AM", "CET"],
            ],
            [(0, "is idle. enabled since Thu Mar 11 14:28:23 2010")],
        ),
    ],
)
def test_check_cups_queues(
    item: str,
    params: Mapping[str, Any],
    string_table: StringTable,
    expected_results: Sequence[Any],
) -> None:
    """Test check function for cups_queues check."""
    with time_machine.travel(datetime.datetime.fromtimestamp(1659514516, tz=ZoneInfo("CET"))):
        parsed = parse_cups_queues(string_table)
        result = list(check_cups_queues(item, params, parsed))

    assert result == expected_results

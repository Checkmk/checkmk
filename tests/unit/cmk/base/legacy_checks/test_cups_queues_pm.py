#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import datetime
from typing import Any
from zoneinfo import ZoneInfo

import time_machine

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.cups_queues import (
    check_cups_queues,
    inventory_cups_queues,
    parse_cups_queues,
)


@time_machine.travel(datetime.datetime.fromtimestamp(1659514516, tz=ZoneInfo("CET")))
def test_discovery_cups_queues_pm() -> None:
    """Test discovery function for cups_queues with active and idle printers."""
    # CUPS printer status data - Pattern 5d (System format)
    string_table: StringTable = [
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
        ["lpr2-2", "root", "1024", "Tue", "28", "Jun", "2010", "01:02:35", "PM", "CET"],
        ["lpr2-3", "root", "1024", "Tue", "29", "Jun", "2010", "09:05:54", "AM", "CET"],
        ["lpr2-4", "root", "1024", "Tue", "Jun", "29", "09:05:56", "2010"],
    ]

    parsed = parse_cups_queues(string_table)
    result = list(inventory_cups_queues(parsed))

    # Should discover both printers
    expected_items = ["lpr2", "spr1"]
    discovered_items = [item for item, _params in result]

    assert len(result) == 2
    assert sorted(discovered_items) == sorted(expected_items)


@time_machine.travel(datetime.datetime.fromtimestamp(1659514516, tz=ZoneInfo("CET")))
def test_check_cups_queues_pm_active_printer() -> None:
    """Test check function for cups_queues with active printer having jobs."""
    string_table: StringTable = [
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
        ["lpr2-2", "root", "1024", "Tue", "28", "Jun", "2010", "01:02:35", "PM", "CET"],
        ["lpr2-3", "root", "1024", "Tue", "29", "Jun", "2010", "09:05:54", "AM", "CET"],
        ["lpr2-4", "root", "1024", "Tue", "Jun", "29", "09:05:56", "2010"],
    ]

    parsed = parse_cups_queues(string_table)

    # Test lpr2 check - now printing with jobs
    params: dict[str, Any] = {
        "disabled_since": 2,
        "is_idle": 0,
        "job_age": (360, 720),
        "job_count": (5, 10),
        "now_printing": 0,
    }

    result = list(check_cups_queues("lpr2", params, parsed))

    # Should return multiple results
    assert len(result) == 3

    # First result: printer status
    assert result[0][0] == 0  # OK state
    assert "now printing lpr2-3" in result[0][1]
    assert "enabled since" in result[0][1]

    # Second result: job count
    assert result[1][0] == 0  # OK state
    assert "Jobs: 3" in result[1][1]
    # Should have performance data for jobs
    assert len(result[1][2]) == 1
    assert result[1][2][0][0] == "jobs"
    assert result[1][2][0][1] == 3

    # Third result: oldest job age (should be critical due to old job)
    assert result[2][0] == 2  # Critical state
    assert "Oldest job is from" in result[2][1]


@time_machine.travel(datetime.datetime.fromtimestamp(1659514516, tz=ZoneInfo("CET")))
def test_check_cups_queues_pm_idle_printer() -> None:
    """Test check function for cups_queues with idle printer."""
    string_table: StringTable = [
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
        ["lpr2-2", "root", "1024", "Tue", "28", "Jun", "2010", "01:02:35", "PM", "CET"],
        ["lpr2-3", "root", "1024", "Tue", "29", "Jun", "2010", "09:05:54", "AM", "CET"],
        ["lpr2-4", "root", "1024", "Tue", "Jun", "29", "09:05:56", "2010"],
    ]

    parsed = parse_cups_queues(string_table)

    # Test spr1 check - idle printer
    params: dict[str, Any] = {
        "disabled_since": 2,
        "is_idle": 0,
        "job_age": (360, 720),
        "job_count": (5, 10),
        "now_printing": 0,
    }

    result = list(check_cups_queues("spr1", params, parsed))

    # Should return single result for idle printer
    assert len(result) == 1

    # Printer status: idle
    assert result[0][0] == 0  # OK state
    assert "is idle" in result[0][1]
    assert "enabled since Thu Mar 11 14:28:23 2010" in result[0][1]

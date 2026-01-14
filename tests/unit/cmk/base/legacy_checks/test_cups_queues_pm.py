#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import datetime
from typing import Any
from zoneinfo import ZoneInfo

import time_machine

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.cups_queues import (
    check_cups_queues,
    discover_cups_queues,
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
    result = list(discover_cups_queues(parsed))

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

    with time_machine.travel(datetime.datetime.fromtimestamp(1659514516, tz=ZoneInfo("CET"))):
        result = list(check_cups_queues("lpr2", params, parsed))

    assert result == [
        (
            0,
            "now printing lpr2-3. enabled since Tue Jun 29 09:22:04 2010 "
            "(Wiederherstellbar: Der Netzwerk-Host lpr2 ist beschaeftigt, erneuter "
            "Versuch in 30 Sekunden)",
        ),
        (0, "Jobs: 3", [("jobs", 3, 5, 10)]),
        (0, "Oldest job is from 2010-06-28 14:02:35"),
        (
            2,
            "Age of oldest job: 12 years 38 days (warn/crit at 6 minutes 0 "
            "seconds/12 minutes 0 seconds)",
            [],
        ),
    ]


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

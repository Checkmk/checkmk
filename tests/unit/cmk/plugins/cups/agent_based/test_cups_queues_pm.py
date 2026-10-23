#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import datetime
from zoneinfo import ZoneInfo

import time_machine

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.cups.agent_based.cups_queues import (
    check_cups_queues,
    discover_cups_queues,
    parse_cups_queues,
)


@time_machine.travel(datetime.datetime.fromtimestamp(1659514516, tz=ZoneInfo("CET")))
def test_discovery_cups_queues_pm() -> None:
    """Test discovery function for cups_queues with active and idle printers."""
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

    assert len(result) == 2
    discovered_items = {s.item for s in result}
    assert discovered_items == {"lpr2", "spr1"}


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

    params: dict[str, object] = {
        "disabled_since": 2,
        "is_idle": 0,
        "job_age": (360, 720),
        "job_count": (5, 10),
        "now_printing": 0,
    }

    with time_machine.travel(datetime.datetime.fromtimestamp(1659514516, tz=ZoneInfo("CET"))):
        results = list(check_cups_queues("lpr2", params, parsed))

    result_objs = [r for r in results if isinstance(r, Result)]
    assert result_objs[0].state == State.OK
    assert "now printing" in result_objs[0].summary
    # Should have job count and age results
    assert len(results) > 1


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

    params: dict[str, object] = {
        "disabled_since": 2,
        "is_idle": 0,
        "job_age": (360, 720),
        "job_count": (5, 10),
        "now_printing": 0,
    }

    results = list(check_cups_queues("spr1", params, parsed))

    result_objs = [r for r in results if isinstance(r, Result)]
    assert len(result_objs) == 1
    assert "is idle" in result_objs[0].summary
    assert "enabled since Thu Mar 11 14:28:23 2010" in result_objs[0].summary

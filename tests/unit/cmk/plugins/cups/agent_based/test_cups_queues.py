#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Mapping
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.cups.agent_based.cups_queues import (
    check_cups_queues,
    discover_cups_queues,
    parse_cups_queues,
)


@pytest.mark.parametrize(
    "string_table, expected_items",
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
            {"lpr2", "spr1"},
        ),
    ],
)
def test_discover_cups_queues(
    string_table: StringTable,
    expected_items: set[str],
) -> None:
    with time_machine.travel(datetime.datetime.fromtimestamp(1659514516, tz=ZoneInfo("CET"))):
        parsed = parse_cups_queues(string_table)
        result = list(discover_cups_queues(parsed))
    assert {s.item for s in result} == expected_items


@pytest.mark.parametrize(
    "item, params, string_table, expected_state, expected_summary_contains",
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
            State.OK,
            "now printing",
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
            State.OK,
            "is idle",
        ),
    ],
)
def test_check_cups_queues(
    item: str,
    params: Mapping[str, object],
    string_table: StringTable,
    expected_state: State,
    expected_summary_contains: str,
) -> None:
    with time_machine.travel(datetime.datetime.fromtimestamp(1659514516, tz=ZoneInfo("CET"))):
        parsed = parse_cups_queues(string_table)
        results = list(check_cups_queues(item, params, parsed))

    result_objs = [r for r in results if isinstance(r, Result)]
    assert result_objs[0].state == expected_state
    assert expected_summary_contains in result_objs[0].summary

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import datetime
from zoneinfo import ZoneInfo

import time_machine

from cmk.base.legacy_checks.cups_queues import (
    check_cups_queues,
    discover_cups_queues,
    parse_cups_queues,
)


def test_cups_queues_am_discovery():
    """Test discovery of CUPS printer queues."""
    # Pattern 5d: System monitoring data (CUPS printer status and job queue)
    string_table = [
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
        ["lpr2-2", "root", "1024", "Tue", "28", "Jun", "2010", "09:05:54", "AM", "CET"],
        ["lpr2-3", "root", "1024", "Tue", "29", "Jun", "2010", "01:02:35", "PM", "CET"],
        ["lpr2-4", "root", "1024", "Tue", "Jun", "29", "09:05:56", "2010"],
    ]

    # Test discovery
    # 2010-06-29 10:00:00
    with time_machine.travel(datetime.datetime.fromtimestamp(1277805600.0, tz=ZoneInfo("CET"))):
        parsed = parse_cups_queues(string_table)
        discovery = list(discover_cups_queues(parsed))
    assert len(discovery) == 2
    items = [item for item, _params in discovery]
    assert "lpr2" in items
    assert "spr1" in items


def test_cups_queues_lpr2_printing():
    """Test CUPS queue check for printer currently printing with jobs."""
    # Pattern 5d: System monitoring data
    string_table = [
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
        ["lpr2-2", "root", "1024", "Tue", "28", "Jun", "2010", "09:05:54", "AM", "CET"],
        ["lpr2-3", "root", "1024", "Tue", "29", "Jun", "2010", "01:02:35", "PM", "CET"],
        ["lpr2-4", "root", "1024", "Tue", "Jun", "29", "09:05:56", "2010"],
    ]

    params = {
        "disabled_since": 2,
        "is_idle": 0,
        "job_age": (360, 720),
        "job_count": (5, 10),
        "now_printing": 0,
    }

    # 2010-06-29 10:00:00
    with time_machine.travel(datetime.datetime.fromtimestamp(1277805600.0, tz=ZoneInfo("CET"))):
        parsed = parse_cups_queues(string_table)
        results = list(check_cups_queues("lpr2", params, parsed))

    # Should contain status message, job count, and old job warning
    assert results == [
        (
            0,
            "now printing lpr2-3. enabled since Tue Jun 29 09:22:04 2010 (Wiederherstellbar: Der Netzwerk-Host lpr2 ist beschaeftigt, erneuter Versuch in 30 Sekunden)",
        ),
        (0, "Jobs: 3", [("jobs", 3, 5, 10)]),
        (0, "Oldest job is from 2010-06-28 10:05:54"),
        (
            2,
            "Age of oldest job: 1 day 1 hour (warn/crit at 6 minutes 0 seconds/12 minutes 0 seconds)",
            [],
        ),
    ]


def test_cups_queues_spr1_idle():
    """Test CUPS queue check for idle printer."""
    # Pattern 5d: System monitoring data
    string_table = [
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
        ["lpr2-2", "root", "1024", "Tue", "28", "Jun", "2010", "09:05:54", "AM", "CET"],
        ["lpr2-3", "root", "1024", "Tue", "29", "Jun", "2010", "01:02:35", "PM", "CET"],
        ["lpr2-4", "root", "1024", "Tue", "Jun", "29", "09:05:56", "2010"],
    ]

    params = {
        "disabled_since": 2,
        "is_idle": 0,
        "job_age": (360, 720),
        "job_count": (5, 10),
        "now_printing": 0,
    }

    # 2010-06-29 10:00:00
    with time_machine.travel(datetime.datetime.fromtimestamp(1277805600.0, tz=ZoneInfo("CET"))):
        parsed = parse_cups_queues(string_table)
        results = list(check_cups_queues("spr1", params, parsed))

    # Should contain only status message for idle printer
    assert len(results) == 1
    assert "is idle" in results[0][1]
    assert "enabled since Thu Mar 11 14:28:23 2010" in results[0][1]

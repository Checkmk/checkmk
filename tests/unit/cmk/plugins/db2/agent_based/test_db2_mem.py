#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State, StringTable
from cmk.plugins.db2.agent_based.db2_mem import check_db2_mem, discover_db2_mem, parse_db2_mem

SECTION = parse_db2_mem(
    [
        ["Instance", "db2inst1"],
        ["Memory", "Limit:", "100", "MB"],
        ["HWM", "usage:", "94208", "KB"],
        ["Instance", "db2inst2"],
        ["Memory", "Limit:", "1000", "bytes"],
        ["HWM", "usage:", "100", "bytes"],
        ["Instance", "db2inst3"],
    ]
)


def test_every_instance_is_discovered() -> None:
    assert list(discover_db2_mem(SECTION)) == [
        Service(item="db2inst1"),
        Service(item="db2inst2"),
        Service(item="db2inst3"),
    ]


def test_free_memory_below_lower_levels_is_warn() -> None:
    assert list(check_db2_mem("db2inst1", {"levels_lower": (10.0, 5.0)}, SECTION)) == [
        Result(state=State.OK, summary="Max 100 MiB"),
        Result(state=State.OK, summary="Used: 92.0 MiB"),
        Metric("mem_used", 92 * 1024**2, boundaries=(0, 100 * 1024**2)),
        Result(state=State.WARN, summary="Free: 8.00% (warn/crit below 10.00%/5.00%)"),
    ]


def test_values_with_unknown_unit_are_taken_as_bytes() -> None:
    assert list(check_db2_mem("db2inst2", {"levels_lower": (10.0, 5.0)}, SECTION)) == [
        Result(state=State.OK, summary="Max 1000 B"),
        Result(state=State.OK, summary="Used: 100 B"),
        Metric("mem_used", 100, boundaries=(0, 1000)),
        Result(state=State.OK, summary="Free: 90.00%"),
    ]


def test_instance_without_memory_lines_yields_nothing() -> None:
    assert not list(check_db2_mem("db2inst3", {"levels_lower": (10.0, 5.0)}, SECTION))


def test_empty_section_is_ignored() -> None:
    empty: StringTable = []

    with pytest.raises(IgnoreResultsError):
        list(check_db2_mem("db2inst1", {"levels_lower": (10.0, 5.0)}, empty))

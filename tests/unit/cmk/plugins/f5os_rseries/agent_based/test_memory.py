#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.f5os_rseries.agent_based.memory import (
    check_f5os_rseries_memory,
    discover_f5os_rseries_memory,
    F5OSMemorySection,
    parse_f5os_rseries_memory,
)

# Walk: used=8909565952, free=2363469824, used%=93, total=16107466752, avail=6833496064
_MEM_STRING_TABLE = [["8909565952", "2363469824", "93", "16107466752", "6833496064"]]


@pytest.mark.parametrize(
    "string_table,expected",
    [
        ([], None),
        (
            _MEM_STRING_TABLE,
            F5OSMemorySection(
                mem_used=8909565952,
                mem_free=2363469824,
                mem_used_percent=93.0,
                mem_total=16107466752,
                mem_avail=6833496064,
            ),
        ),
    ],
)
def test_parse_f5os_rseries_memory(
    string_table: StringTable, expected: F5OSMemorySection | None
) -> None:
    assert parse_f5os_rseries_memory(string_table) == expected


def test_discover_f5os_rseries_memory() -> None:
    section = parse_f5os_rseries_memory(_MEM_STRING_TABLE)
    assert section is not None
    assert list(discover_f5os_rseries_memory(section)) == [Service()]


def test_check_f5os_rseries_memory_crit() -> None:
    section = parse_f5os_rseries_memory(_MEM_STRING_TABLE)
    assert section is not None
    # 93% used exceeds default WARN=80 CRIT=90
    results = list(check_f5os_rseries_memory({"levels": (80.0, 90.0)}, section))
    assert any(isinstance(r, Result) and r.state == State.CRIT for r in results)
    assert any(isinstance(r, Metric) and r.name == "mem_used_percent" for r in results)


def test_parse_f5os_rseries_memory_malformed_raises() -> None:
    # An unreadable usage column is unexpected per the MIB and must surface, not be
    # coerced into a fabricated healthy 0%.
    with pytest.raises(ValueError):
        parse_f5os_rseries_memory([["8909565952", "2363469824", "", "16107466752", "6833496064"]])

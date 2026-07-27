#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.f5os_rseries.agent_based import cpu as cpu_module
from cmk.plugins.f5os_rseries.agent_based.cpu import (
    check_f5os_rseries_cpu,
    discover_f5os_rseries_cpu,
    F5OSCPUSection,
    parse_f5os_rseries_cpu,
)

# Walk: .2="12" → 12% current, .3="13" → 13% 5s avg, .4="8" → 8% 1m avg, .5="8" → 8% 5m avg
_CPU_STRING_TABLE = [["cpu", "12", "13", "8", "8"]]


@pytest.mark.parametrize(
    "string_table,expected",
    [
        ([], None),
        (
            _CPU_STRING_TABLE,
            F5OSCPUSection(current=12.0, avg_5sec=13.0, avg_1min=8.0, avg_5min=8.0),
        ),
    ],
)
def test_parse_f5os_rseries_cpu(string_table: StringTable, expected: F5OSCPUSection | None) -> None:
    assert parse_f5os_rseries_cpu(string_table) == expected


def test_discover_f5os_rseries_cpu() -> None:
    section = parse_f5os_rseries_cpu(_CPU_STRING_TABLE)
    assert section is not None
    assert list(discover_f5os_rseries_cpu(section)) == [Service()]


def test_check_f5os_rseries_cpu_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cpu_module, "get_value_store", dict)
    section = parse_f5os_rseries_cpu(_CPU_STRING_TABLE)
    assert section is not None
    results = list(check_f5os_rseries_cpu({"util": (80.0, 90.0)}, section))
    assert any(isinstance(r, Result) and r.state == State.OK for r in results)
    assert any(isinstance(r, Metric) and r.name == "util" for r in results)


def test_check_f5os_rseries_cpu_warn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cpu_module, "get_value_store", dict)
    high_section = F5OSCPUSection(current=85.0, avg_5sec=84.0, avg_1min=82.0, avg_5min=80.0)
    results = list(check_f5os_rseries_cpu({"util": (80.0, 90.0)}, high_section))
    assert any(isinstance(r, Result) and r.state == State.WARN for r in results)


def test_parse_f5os_rseries_cpu_malformed_raises() -> None:
    # The MIB guarantees these utilization columns are numeric. A non-numeric value is
    # unexpected and must surface (crash report) rather than be coerced to a fabricated
    # reading that would either look healthy (0%) or invent an "unknown" state.
    with pytest.raises(ValueError):
        parse_f5os_rseries_cpu([["cpu", "12", "13", "N/A", "8"]])

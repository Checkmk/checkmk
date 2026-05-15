#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest
import time_machine

import cmk.legacy_checks.netscaler_cpu as netscaler_cpu_plugin
from cmk.agent_based.v2 import CheckResult, Metric, Result, State, StringTable
from cmk.legacy_checks.netscaler_cpu import (
    check_netscaler_cpu,
    discover_netscaler_cpu,
    parse_netscaler_cpu,
)

_SECTION = [["MgmtCPU", "20"], ["PacketCPU", "55"]]


def test_parse_netscaler_cpu() -> None:
    assert parse_netscaler_cpu(_SECTION) == _SECTION


def test_discover_netscaler_cpu() -> None:
    assert list(discover_netscaler_cpu(_SECTION)) == [("MgmtCPU", {}), ("PacketCPU", {})]


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        pytest.param(
            "MgmtCPU",
            {"levels": (90.0, 95.0)},
            [["MgmtCPU", "20"]],
            [
                Result(state=State.OK, summary="Total CPU: 20.00%"),
                Metric(name="util", value=20.0, levels=(90.0, 95.0), boundaries=(0, None)),
            ],
            id="ok_below_thresholds",
        ),
        pytest.param(
            "MgmtCPU",
            {"levels": (90.0, 95.0)},
            [["MgmtCPU", "97"]],
            [
                Result(state=State.CRIT, summary="Total CPU: 97.00% (warn/crit at 90.00%/95.00%)"),
                Metric(name="util", value=97.0, levels=(90.0, 95.0), boundaries=(0, None)),
            ],
            id="crit_above_critical_threshold",
        ),
    ],
)
def test_check_netscaler_cpu(
    item: str,
    params: Mapping[str, Any],
    string_table: StringTable,
    expected_results: Sequence[CheckResult],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value_store: dict[str, tuple[float, float]] = {}
    monkeypatch.setattr(netscaler_cpu_plugin, "get_value_store", lambda: value_store)
    with time_machine.travel("2026-01-01 00:00:00", tick=False):
        result = list(check_netscaler_cpu(item, params, string_table))
    assert result == expected_results

#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.f5_bigip.agent_based import f5_bigip_cpu_temp
from cmk.plugins.f5_bigip.agent_based.f5_bigip_cpu_temp import (
    check_f5_bigip_cpu_temp,
    discover_f5_bigip_cpu_temp,
    parse_f5_bigip_cpu_temp,
)
from cmk.plugins.lib.temperature import TempParamDict


@pytest.fixture(autouse=True)
def _patch_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f5_bigip_cpu_temp, "get_value_store", dict)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["1", "40"]], [Service(item="1")]),
    ],
)
def test_discover_f5_bigip_cpu_temp(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for f5_bigip_cpu_temp check."""
    section = parse_f5_bigip_cpu_temp(string_table)
    assert list(discover_f5_bigip_cpu_temp(section)) == expected_discoveries


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        pytest.param(
            "1",
            {"levels": (60.0, 80.0)},
            [["1", "40"]],
            [
                Metric("temp", 40.0, levels=(60.0, 80.0)),
                Result(state=State.OK, summary="Temperature: 40 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="ok",
        ),
        pytest.param(
            "2",
            {"levels": (60.0, 80.0)},
            [["1", "40"]],
            [],
            id="unknown item",
        ),
    ],
)
def test_check_f5_bigip_cpu_temp(
    item: str,
    params: TempParamDict,
    string_table: StringTable,
    expected_results: Sequence[Result | Metric],
) -> None:
    """Test check function for f5_bigip_cpu_temp check."""
    section = parse_f5_bigip_cpu_temp(string_table)
    assert list(check_f5_bigip_cpu_temp(item, params, section)) == expected_results

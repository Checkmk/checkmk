#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.quanta.agent_based.quanta_temperature import (
    check_quanta_temperature,
    discover_quanta_temperature,
)
from cmk.plugins.quanta.lib import parse_quanta


@pytest.fixture
def empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.plugins.quanta.agent_based.quanta_temperature.get_value_store",
        dict,
    )


_INFO: list[StringTable] = [
    [
        ["1", "3", "Temp_PCI1_Outlet\x01", "41", "85", "80", "-99", "-99"],
        ["2", "3", "Temp_CPU0_Inlet", "37", "75", "70", "-99", "-99"],
        ["2", "3", "Temp_CPU1_Inlet", "37", "75", "-99", "-99", "-99"],
        ["7", "1", "Temp_DIMM_AB", "-99", "85", "84", "-99", "-99"],
        ["7", "2", "Temp_DIMM_CD", "-99", "85", "84", "95", "100"],
    ]
]


def test_discover_quanta_temperature() -> None:
    parsed = parse_quanta(_INFO)
    result = sorted(discover_quanta_temperature(parsed), key=lambda s: s.item or "")
    assert result == [
        Service(item="Temp_CPU0_Inlet"),
        Service(item="Temp_CPU1_Inlet"),
        Service(item="Temp_DIMM_AB"),
        Service(item="Temp_DIMM_CD"),
        Service(item="Temp_PCI1_Outlet"),
    ]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        (
            "Temp_CPU0_Inlet",
            [
                Metric("temp", 37.0, levels=(70.0, 75.0)),
                Result(state=State.OK, summary="Temperature: 37.0 °C"),
                Result(state=State.OK, notice="State on device: OK"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
            ],
        ),
        (
            "Temp_DIMM_AB",
            [Result(state=State.WARN, summary="Status: other")],
        ),
        (
            "Temp_DIMM_CD",
            [Result(state=State.UNKNOWN, summary="Status: unknown")],
        ),
        (
            "Temp_PCI1_Outlet",
            [
                Metric("temp", 41.0, levels=(80.0, 85.0)),
                Result(state=State.OK, summary="Temperature: 41.0 °C"),
                Result(state=State.OK, notice="State on device: OK"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
            ],
        ),
    ],
)
def test_check_quanta_temperature(
    item: str, expected_results: Sequence[object], empty_value_store: None
) -> None:
    parsed = parse_quanta(_INFO)
    result = list(check_quanta_temperature(item, {}, parsed))
    assert result == expected_results

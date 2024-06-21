#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based import extreme_vsp_switches_temperature
from cmk.plugins.collection.agent_based.extreme_vsp_switches_temperature import (
    check_vsp_switches_temperature,
    discover_vsp_switches_temperature,
    parse_vsp_switches_temperature,
)
from cmk.plugins.lib.temperature import TempParamType

_STRING_TABLE = [
    ["INTERNAL MAC", "61"],
    ["PHY1", "38"],
    ["PHY2", "52"],
    ["PHY3", "65"],
]


@pytest.mark.parametrize(
    "string_table, expected_discovery_result",
    [
        pytest.param(
            _STRING_TABLE,
            [
                Service(item="INTERNAL MAC"),
                Service(item="PHY1"),
                Service(item="PHY2"),
                Service(item="PHY3"),
            ],
            id="For every switch available, a Service is created.",
        ),
        pytest.param(
            [],
            [],
            id="If the are no switches, no Services are created.",
        ),
    ],
)
def test_discover_vsp_switches_temperature(
    string_table: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert (
        list(discover_vsp_switches_temperature(parse_vsp_switches_temperature(string_table)))
        == expected_discovery_result
    )


@pytest.fixture(name="value_store_patch")
def value_store_fixture(monkeypatch):
    value_store_patched = {
        "vsp_switch_PHY1": (30, 40),
    }
    monkeypatch.setattr(
        extreme_vsp_switches_temperature, "get_value_store", lambda: value_store_patched
    )
    yield value_store_patched


@pytest.mark.usefixtures("value_store_patch")
@pytest.mark.parametrize(
    "string_table, item, params, expected_check_result",
    [
        pytest.param(
            _STRING_TABLE,
            "PHY1",
            {"levels": (50.0, 60.0)},
            [
                Metric("temp", 38.0, levels=(50.0, 60.0)),
                Result(state=State.OK, summary="Temperature: 38.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="The temperature is below the WARN/CRIT levels, so the check state is OK.",
        ),
        pytest.param(
            _STRING_TABLE,
            "PHY2",
            {"levels": (50.0, 60.0)},
            [
                Metric("temp", 52.0, levels=(50.0, 60.0)),
                Result(
                    state=State.WARN, summary="Temperature: 52.0 °C (warn/crit at 50.0 °C/60.0 °C)"
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="The temperature is above the WARN, so the check state is WARN.",
        ),
        pytest.param(
            _STRING_TABLE,
            "PHY3",
            {"levels": (50.0, 60.0)},
            [
                Metric("temp", 65.0, levels=(50.0, 60.0)),
                Result(
                    state=State.CRIT, summary="Temperature: 65.0 °C (warn/crit at 50.0 °C/60.0 °C)"
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="The temperature is above the CRIT, so the check state is CRIT.",
        ),
    ],
)
def test_check_vsp_switches_temperature(
    string_table: StringTable,
    item: str,
    params: TempParamType,
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_vsp_switches_temperature(
                item=item,
                params=params,
                section=parse_vsp_switches_temperature(string_table),
            )
        )
        == expected_check_result
    )

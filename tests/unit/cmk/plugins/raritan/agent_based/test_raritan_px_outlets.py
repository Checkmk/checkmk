#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.raritan.agent_based.raritan_px_outlets import (
    check_raritan_px_outlets,
    discover_raritan_px_outlets,
    parse_raritan_px_outlets,
)

_STRING_TABLE = [
    ["3", "label", "1", "3", "3", "3", "3", "3"],
    ["2", "", "1", "3", "3", "3", "3", "3"],
    ["4", "", "0", "3", "3", "3", "3", "3"],
]


def test_parse_raritan_px_outlets() -> None:
    section = parse_raritan_px_outlets(_STRING_TABLE)
    assert section["3"].label == "label"
    assert section["3"].elphase.device_state == (State.OK, "on")
    # current and voltage are scaled, the remaining readings are not
    assert section["3"].elphase.current is not None
    assert section["3"].elphase.current.value == 0.003
    assert section["3"].elphase.voltage is not None
    assert section["3"].elphase.voltage.value == 0.003
    assert section["3"].elphase.power is not None
    assert section["3"].elphase.power.value == 3.0
    assert section["3"].elphase.appower is not None
    assert section["3"].elphase.appower.value == 3.0
    assert section["3"].elphase.energy is not None
    assert section["3"].elphase.energy.value == 3.0


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        pytest.param(
            _STRING_TABLE,
            [Service(item="3"), Service(item="2")],
            id="outlets which are off are not discovered",
        ),
    ],
)
def test_discover_raritan_px_outlets(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    parsed = parse_raritan_px_outlets(string_table)
    assert list(discover_raritan_px_outlets(parsed)) == list(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, expected_results",
    [
        pytest.param(
            "3",
            {},
            [
                Result(state=State.OK, summary="[label]"),
                Result(state=State.OK, summary="Device status: on(0)"),
                Result(state=State.OK, summary="Voltage: 0.0 V"),
                Metric("voltage", 0.003),
                Result(state=State.OK, summary="Current: 0.0 A"),
                Metric("current", 0.003),
                Result(state=State.OK, summary="Power: 3.0 W"),
                Metric("power", 3.0),
                Result(state=State.OK, summary="Apparent Power: 3.0 VA"),
                Metric("appower", 3.0),
                Result(state=State.OK, summary="Energy: 3.0 Wh"),
                Metric("energy", 3.0),
            ],
            id="outlet with label",
        ),
        pytest.param(
            "2",
            {},
            [
                Result(state=State.OK, summary="Device status: on(0)"),
                Result(state=State.OK, summary="Voltage: 0.0 V"),
                Metric("voltage", 0.003),
                Result(state=State.OK, summary="Current: 0.0 A"),
                Metric("current", 0.003),
                Result(state=State.OK, summary="Power: 3.0 W"),
                Metric("power", 3.0),
                Result(state=State.OK, summary="Apparent Power: 3.0 VA"),
                Metric("appower", 3.0),
                Result(state=State.OK, summary="Energy: 3.0 Wh"),
                Metric("energy", 3.0),
            ],
            id="outlet without label",
        ),
        pytest.param("999", {}, [], id="unknown item"),
    ],
)
def test_check_raritan_px_outlets(
    item: str,
    params: Mapping[str, object],
    expected_results: Sequence[Result | Metric],
) -> None:
    parsed = parse_raritan_px_outlets(_STRING_TABLE)
    assert list(check_raritan_px_outlets(item, params, parsed)) == list(expected_results)

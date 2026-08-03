#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.plugins.viprinet.agent_based.viprinet_temp as viprinet_temp_plugin
from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.viprinet.agent_based.viprinet_temp import (
    check_viprinet_temp,
    discover_viprinet_temp,
    parse_viprinet_temp,
)

_STRING_TABLE = [["35", "40"]]


def test_discover_viprinet_temp() -> None:
    section = parse_viprinet_temp(_STRING_TABLE)
    assert list(discover_viprinet_temp(section)) == [
        Service(item="CPU"),
        Service(item="System"),
    ]


def test_discover_viprinet_temp_no_data() -> None:
    section = parse_viprinet_temp([])
    assert list(discover_viprinet_temp(section)) == []


@pytest.mark.parametrize(
    "item, expected_reading",
    [
        ("CPU", 35.0),
        ("System", 40.0),
    ],
)
def test_check_viprinet_temp(
    item: str,
    expected_reading: float,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value_store: dict[str, object] = {}
    monkeypatch.setattr(viprinet_temp_plugin, "get_value_store", lambda: value_store)
    section = parse_viprinet_temp(_STRING_TABLE)

    value = list(check_viprinet_temp(item, {}, section))
    expected = [
        Metric("temp", expected_reading),
        Result(state=State.OK, summary=f"Temperature: {expected_reading:.0f} °C"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (no levels found)",
        ),
    ]

    assert value == expected

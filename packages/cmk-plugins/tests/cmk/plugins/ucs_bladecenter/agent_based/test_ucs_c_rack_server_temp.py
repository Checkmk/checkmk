#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.ucs_bladecenter.agent_based import ucs_c_rack_server_temp
from cmk.plugins.ucs_bladecenter.agent_based.ucs_c_rack_server_temp import (
    check_ucs_c_rack_server_temp,
    discover_ucs_c_rack_server_temp,
    parse_ucs_c_rack_server_temp,
)

_SECTION = parse_ucs_c_rack_server_temp(
    [
        [
            "processorEnvStats",
            "dn sys/rack-unit-1/board/cpu-1/env-stats",
            "id 1",
            "description x",
            "temperature 58.4",
        ],
        [
            "memoryUnitEnvStats",
            "dn sys/rack-unit-1/board/memarray-1/mem-1/dimm-env-stats",
            "id 1",
            "description x",
            "temperature 40.4",
        ],
        [
            "computeRackUnitMbTempStats",
            "dn sys/rack-unit-1/board/temp-stats",
            "ambientTemp 50.0",
            "frontTemp 50.0",
        ],
        ["somethingElse", "dn sys/rack-unit-1/whatever", "id 1"],  # not a sensor, skipped
    ]
)


@pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse]
def _empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    # Without previous readings the temperature helper reports no trends.
    monkeypatch.setattr(ucs_c_rack_server_temp, "get_value_store", dict)


def test_parse_ucs_c_rack_server_temp() -> None:
    assert _SECTION == {
        "Rack Unit 1 CPU 1": 58.4,
        "Rack Unit 1 Memory Array 1 Memory DIMM 1": 40.4,
        "Rack Unit 1 Motherboard": 50.0,
    }


def test_discover_ucs_c_rack_server_temp() -> None:
    assert list(discover_ucs_c_rack_server_temp(_SECTION)) == [
        Service(item="Rack Unit 1 CPU 1"),
        Service(item="Rack Unit 1 Memory Array 1 Memory DIMM 1"),
        Service(item="Rack Unit 1 Motherboard"),
    ]


def test_check_ucs_c_rack_server_temp_without_levels() -> None:
    results = list(
        check_ucs_c_rack_server_temp("Rack Unit 1 Memory Array 1 Memory DIMM 1", {}, _SECTION)
    )
    assert results[:2] == [
        Metric("temp", 40.4),
        Result(state=State.OK, summary="Temperature: 40.4 °C"),
    ]


def test_check_ucs_c_rack_server_temp_above_levels() -> None:
    results = list(
        check_ucs_c_rack_server_temp("Rack Unit 1 CPU 1", {"levels": (45.0, 55.0)}, _SECTION)
    )
    assert results[:2] == [
        Metric("temp", 58.4, levels=(45.0, 55.0)),
        Result(state=State.CRIT, summary="Temperature: 58.4 °C (warn/crit at 45.0 °C/55.0 °C)"),
    ]


def test_check_ucs_c_rack_server_temp_vanished_item() -> None:
    assert not list(check_ucs_c_rack_server_temp("Rack Unit 2 CPU 1", {}, _SECTION))

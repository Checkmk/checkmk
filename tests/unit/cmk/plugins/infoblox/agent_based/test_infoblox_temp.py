#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from pathlib import Path

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.infoblox.agent_based.infoblox_temp import (
    check_temp,
    discover_infoblox_temp,
    snmp_section_infoblox_temp,
    TempDescr,
)
from cmk.plugins.lib.temperature import TempParamType

from tests.unit.cmk.plugins.collection.agent_based.snmp import get_parsed_snmp_section
from tests.unit.cmk.plugins.lib.test_temperature import mock_value_store

WALK_NIOS_7_2_7 = """
.1.3.6.1.4.1.7779.3.1.1.2.1.7.0 7.2.7
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.37 5
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.38 1
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.39 1
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.40 5
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.41 1
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.37 No power information available.
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.38 The NTP service resumed synchronization.
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.39 CPU_TEMP: +36.00 C
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.40 No temperature information available.
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.41 SYS_TEMP: +34.00 C
"""


WALK_NIOS_9_0_3 = """
.1.3.6.1.4.1.7779.3.1.1.2.1.7.0 9.0.3-50212
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.37 1
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.38 5
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.39 1
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.40 5
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.41 1
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.37 CPU_TEMP: +36.00 C
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.38 No temperature information available.
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.39 SYS_TEMP: +34.00 C
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.40
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.41 CPU Usage: 20%
"""


@pytest.mark.parametrize(
    ["input_walk"],
    [
        pytest.param(WALK_NIOS_7_2_7, id="Nios 7.2.7"),
        pytest.param(WALK_NIOS_9_0_3, id="Nios 9.0.3"),
    ],
)
def test_parse_infoblox_temp(input_walk: str, as_path: Callable[[str], Path]) -> None:
    section = get_parsed_snmp_section(snmp_section_infoblox_temp, as_path(input_walk))
    assert section == {
        "CPU_TEMP 1": TempDescr(reading=36.0, state=(0, "working"), unit="c"),
        "SYS_TEMP": TempDescr(reading=34.0, state=(0, "working"), unit="c"),
    }


@pytest.mark.parametrize(
    ["input_walk"],
    [
        pytest.param(WALK_NIOS_7_2_7, id="Nios 7.2.7"),
        pytest.param(WALK_NIOS_9_0_3, id="Nios 9.0.3"),
    ],
)
def test_inventory_infoblox_temp(input_walk: str, as_path: Callable[[str], Path]) -> None:
    section = get_parsed_snmp_section(snmp_section_infoblox_temp, as_path(input_walk))
    assert section is not None
    assert list(discover_infoblox_temp(section)) == [
        Service(item="CPU_TEMP 1"),
        Service(item="SYS_TEMP"),
    ]


@pytest.mark.parametrize(
    ["input_walk"],
    [
        pytest.param(WALK_NIOS_7_2_7, id="Nios 7.2.7"),
        pytest.param(WALK_NIOS_9_0_3, id="Nios 9.0.3"),
    ],
)
@pytest.mark.parametrize(
    ["item", "params", "expected"],
    [
        pytest.param(
            "CPU_TEMP 1",
            {"levels": (40.0, 50.0)},
            [
                Metric(name="temp", value=36.0, levels=(40.0, 50.0)),
                Result(
                    state=State.OK,
                    summary="Temperature: 36.0 °C",
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="ok",
        ),
        pytest.param(
            "SYS_TEMP",
            {"levels": (30.0, 40.0)},
            [
                Metric(name="temp", value=34.0, levels=(30.0, 40.0)),
                Result(
                    state=State.WARN,
                    summary="Temperature: 34.0 °C (warn/crit at 30.0 °C/40.0 °C)",
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="warning",
        ),
        pytest.param(
            "SYS_TEMP",
            {"levels": (20.0, 30.0)},
            [
                Metric(name="temp", value=34.0, levels=(20.0, 30.0)),
                Result(
                    state=State.CRIT,
                    summary="Temperature: 34.0 °C (warn/crit at 20.0 °C/30.0 °C)",
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="error",
        ),
    ],
)
def test_check_infoblox_temp(
    input_walk: str,
    item: str,
    params: TempParamType,
    expected: list,
    as_path: Callable[[str], Path],
) -> None:
    section = get_parsed_snmp_section(snmp_section_infoblox_temp, as_path(input_walk))
    assert section is not None

    assert list(check_temp(item, params, section, mock_value_store())) == expected

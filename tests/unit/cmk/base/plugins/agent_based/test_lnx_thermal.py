#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Optional, Sequence, Union

import pytest

from cmk.base.plugins.agent_based import lnx_thermal
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


def splitter(text: str, split_symbol: Optional[str] = None) -> Sequence[Sequence[str]]:
    return [line.split(split_symbol) for line in text.split("\n")]


AGENT_INFO = [
    splitter(
        """thermal_zone0 enabled acpitz 57000 127000 critical
thermal_zone1 enabled acpitz 65000 100000 critical 95500 passive
thermal_zone3 - pch_skylake 46000 115000 critical
thermal_zone5 pkg-temp-0  44000 0 passive 0 passive"""
    ),
    splitter(
        """thermal_zone0|enabled|acpitz|25000|107000|critical
thermal_zone3|-|pch_skylake|45000|115000|critical
thermal_zone4|-|INT3400 Thermal|20000
thermal_zone5|-|x86_pkg_temp|48000|0|passive|0|passive
thermal_zone6|-|B0D4|61000|127000|critical|127000|hot|99000|passive|99000|active|94000|active
thermal_zone8|-|sunxi-therm|61|127|critical|127|hot|99|passive|99|active|94|active""",
        "|",
    ),
]

RESULT_DISCOVERY = [
    [Service(item="Zone %s" % i) for i in [0, 1, 3, 5]],
    [Service(item="Zone %s" % i) for i in [0, 3, 4, 5, 6, 8]],
]


@pytest.mark.parametrize("string_table, result", list(zip(AGENT_INFO, RESULT_DISCOVERY)))
def test_parse_and_discovery_function(string_table: StringTable, result: Sequence[Service]) -> None:
    section = lnx_thermal.parse_lnx_thermal(string_table)
    assert list(lnx_thermal.discover_lnx_thermal(section)) == result


RESULT_CHECK = [
    [
        [
            Metric("temp", 57.0, levels=(127.0, 127.0)),
            Result(state=State.OK, summary="Temperature: 57.0°C"),
            Result(
                state=State.OK,
                notice="Configuration: prefer user levels over device levels (used device levels)",
            ),
        ],
        [
            Metric("temp", 65.0, levels=(95.5, 100.0)),
            Result(state=State.OK, summary="Temperature: 65.0°C"),
            Result(
                state=State.OK,
                notice="Configuration: prefer user levels over device levels (used device levels)",
            ),
        ],
        [
            Metric("temp", 46.0, levels=(115.0, 115.0)),
            Result(state=State.OK, summary="Temperature: 46.0°C"),
            Result(
                state=State.OK,
                notice="Configuration: prefer user levels over device levels (used device levels)",
            ),
        ],
        [
            Metric("temp", 44.0, levels=None),
            Result(state=State.OK, summary="Temperature: 44.0°C"),
            Result(
                state=State.OK,
                notice="Configuration: prefer user levels over device levels (no levels found)",
            ),
        ],
    ],
    [
        [
            Metric("temp", 25.0, levels=(107.0, 107.0)),
            Result(state=State.OK, summary="Temperature: 25.0°C"),
            Result(
                state=State.OK,
                notice="Configuration: prefer user levels over device levels (used device levels)",
            ),
        ],
        [
            Metric("temp", 45.0, levels=(115.0, 115.0)),
            Result(state=State.OK, summary="Temperature: 45.0°C"),
            Result(
                state=State.OK,
                notice="Configuration: prefer user levels over device levels (used device levels)",
            ),
        ],
        [
            Metric("temp", 20.0, levels=None),
            Result(state=State.OK, summary="Temperature: 20.0°C"),
            Result(
                state=State.OK,
                notice="Configuration: prefer user levels over device levels (no levels found)",
            ),
        ],
        [
            Metric("temp", 48.0, levels=None),
            Result(state=State.OK, summary="Temperature: 48.0°C"),
            Result(
                state=State.OK,
                notice="Configuration: prefer user levels over device levels (no levels found)",
            ),
        ],
        [
            Metric("temp", 61.0, levels=(99.0, 127.0)),
            Result(state=State.OK, summary="Temperature: 61.0°C"),
            Result(
                state=State.OK,
                notice="Configuration: prefer user levels over device levels (used device levels)",
            ),
        ],
        [
            Metric("temp", 61.0, levels=(99.0, 127.0)),
            Result(state=State.OK, summary="Temperature: 61.0°C"),
            Result(
                state=State.OK,
                notice="Configuration: prefer user levels over device levels (used device levels)",
            ),
        ],
    ],
]


@pytest.mark.parametrize(
    "string_table, discovered, results", list(zip(AGENT_INFO, RESULT_DISCOVERY, RESULT_CHECK))
)
def test_check_functions_perfdata(
    string_table: StringTable, discovered: Sequence[Service], results
) -> None:
    section = lnx_thermal.parse_lnx_thermal(string_table)
    for service, result in zip(discovered, results):
        assert isinstance(service.item, str)
        assert list(lnx_thermal.check_lnx_thermal(service.item, {}, section)) == result


@pytest.mark.parametrize(
    "line, item",
    [
        (
            [
                "thermal_zone0",
                "enabled",
                "acpitz",
                "27800",
                "105000",
                "critical",
                "80000",
                "active",
                "55000",
                "active",
                "500",
                "00",
                "active",
                "45000",
                "active",
                "40000",
                "active",
            ],
            "Zone 0",
        ),
        (
            [
                "thermal_zone1",
                "enabled",
                "acpitz",
                "29800",
                "105000",
                "critical",
                "108000",
                "passive",
            ],
            "Zone 1",
        ),
    ],
)
def test_parse_and_discovery_function_2(line: List[str], item: str):
    section = lnx_thermal.parse_lnx_thermal([line])
    assert list(lnx_thermal.discover_lnx_thermal(section)) == [Service(item=item)]


@pytest.mark.parametrize(
    "line",
    [
        (
            [
                "thermal_zone1",
                "-",
                "pkg-temp-0",
                "",
                "35000",
                "0",
                "passive",
                "0",
                "passive",
            ],
        ),
    ],
)
def test_parse_and_discovery_function_2_no_item(line: List[str]) -> None:
    section = lnx_thermal.parse_lnx_thermal([line])
    assert list(lnx_thermal.discover_lnx_thermal(section)) == []


@pytest.mark.parametrize(
    "line, item, result",
    [
        (
            [
                "thermal_zone0",
                "enabled",
                "acpitz",
                "27800",
                "105000",
                "critical",
                "80000",
                "active",
                "55000",
                "active",
                "500",
                "00",
                "active",
                "45000",
                "active",
                "40000",
                "active",
            ],
            "Zone 0",
            [
                Metric("temp", 27.8, levels=None),
                Result(state=State.OK, summary="Temperature: 27.8\xb0C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (no levels found)",
                ),
            ],
        ),
        (
            [
                "thermal_zone1",
                "enabled",
                "acpitz",
                "29800",
                "105000",
                "critical",
                "108000",
                "passive",
            ],
            "Zone 1",
            [
                Metric("temp", 29.8, levels=(108.0, 105.0)),
                Result(state=State.OK, summary="Temperature: 29.8\xb0C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
            ],
        ),
    ],
)
def test_check_functions_perfdata_2(
    line: List[str], item: str, result: List[Union[Metric, Result]]
) -> None:
    section = lnx_thermal.parse_lnx_thermal([line])
    assert list(lnx_thermal.check_lnx_thermal(item, {}, section)) == result

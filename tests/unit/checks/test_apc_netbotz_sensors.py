#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.sectionname import SectionName

from cmk.checkengine.checking import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State

TEST_INFO: Sequence[Sequence[Sequence[str]]] = [
    [
        ["nbAlinkEnc_0_4_TEMP", "252", "Temp 03.01.190-19 (4)", "25.200000"],
        ["nbAlinkEnc_0_5_TEMP", "0", "Temperature  (5)", ""],
    ],
    [
        ["nbAlinkEnc_1_5_HUMI", "370", "Hum 03.01.190-25 (5)", "37.000000"],
        ["nbAlinkEnc_0_6_HUMI", "0", "Humidity  (6)", ""],
    ],
    [
        ["nbAlinkEnc_0_5_DWPT", "0", "Dew Point  (5)", ""],
        ["nbAlinkEnc_0_3_DWPT", "61", "Dew Point  (3)", "6.100000"],
    ],
]


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "nbAlinkEnc_0_4_TEMP",
            {"output_unit": "k", "levels": (18.0, 25.0), "levels_lower": (-4.0, -6.0)},
            [
                Result(
                    state=State.CRIT,
                    summary="[Temp 03.01.190-19 (4)] 298.3 K (warn/crit at 291.1/298.1 K) (warn/crit below 269.1/267.1 K)",
                ),
                Metric("temp", 25.2, levels=(18.0, 25.0)),
            ],
            id="temp reading",
        ),
        pytest.param("nbAlinkEnc_0_5_TEMP", {}, [], id="temp reading not present"),
        pytest.param("nbAlinkEnc_0_3_DWPT", {}, [], id="dew reading"),
    ],
)
def test_apc_netbotz_sensors(
    fix_register: FixRegister,
    item: str,
    params: Mapping[str, object],
    expected_result: Sequence[Result | Metric],
) -> None:
    section_plugin = fix_register.snmp_sections[SectionName("apc_netbotz_sensors")]
    parsed = section_plugin.parse_function(TEST_INFO)
    check_plugin = fix_register.check_plugins[CheckPluginName("apc_netbotz_sensors")]
    result = list(check_plugin.check_function(item=item, params=params, section=parsed))
    assert result == expected_result


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "nbAlinkEnc_1_5_HUMI",
            {"levels": (1.0, 2.0), "levels_lower": (3.0, 4.0)},
            [
                Result(
                    state=State.CRIT,
                    summary="[Hum 03.01.190-25 (5)] 37.00% (warn/crit at 1.00%/2.00%)",
                ),
                Metric("humidity", 37.0, levels=(1.0, 2.0), boundaries=(0.0, 100.0)),
            ],
            id="humidity reading",
        ),
        pytest.param("nbAlinkEnc_0_6_HUMI", {}, [], id="humidity reading not present"),
    ],
)
def test_apc_netbotz_sensors_humidity(
    fix_register: FixRegister,
    item: str,
    params: Mapping[str, object],
    expected_result: Sequence[Result | Metric],
) -> None:
    section_plugin = fix_register.snmp_sections[SectionName("apc_netbotz_sensors")]
    parsed = section_plugin.parse_function(TEST_INFO)
    check_plugin = fix_register.check_plugins[CheckPluginName("apc_netbotz_sensors_humidity")]
    result = list(check_plugin.check_function(item=item, params=params, section=parsed))
    assert result == expected_result


@pytest.mark.parametrize(
    "item, expected_result",
    [
        pytest.param(
            "nbAlinkEnc_0_3_DWPT",
            [
                Result(state=State.OK, summary="[Dew Point  (3)] 6.1 °C"),
                Metric("temp", 6.1),
            ],
            id="dewpoint reading",
        ),
        pytest.param("nbAlinkEnc_0_5_DWPT", [], id="dewpoint reading not present"),
    ],
)
def test_apc_netbotz_sensors_dewpoint(
    fix_register: FixRegister,
    item: str,
    expected_result: Sequence[Result | Metric],
) -> None:
    section_plugin = fix_register.snmp_sections[SectionName("apc_netbotz_sensors")]
    parsed = section_plugin.parse_function(TEST_INFO)
    check_plugin = fix_register.check_plugins[CheckPluginName("apc_netbotz_sensors_dewpoint")]
    result = list(check_plugin.check_function(item=item, params={}, section=parsed))
    assert result == expected_result

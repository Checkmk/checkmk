#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import SNMPSectionPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.utils.temperature import TempParamDict


@pytest.fixture(name="section_plugin", scope="module")
def _section_plugin(fix_register: FixRegister) -> SNMPSectionPlugin:
    return fix_register.snmp_sections[SectionName("liebert_temp_fluid")]


@pytest.fixture(name="check_plugin", scope="module")
def _check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("liebert_temp_fluid")]


@pytest.fixture(name="section", scope="module")
def _section(section_plugin: SNMPSectionPlugin) -> Mapping[str, tuple[float, str]]:
    return section_plugin.parse_function(
        [
            [
                [
                    "Supply Fluid Temp Set Point 1",
                    "14.0",
                    "deg C",
                    "Supply Fluid Temp Set Point 2",
                    "-6",
                    "deg C",
                    "Supply Fluid Over Temp Alarm Threshold",
                    "0",
                    "deg C",
                    "Supply Fluid Under Temp Warning Threshold",
                    "0",
                    "deg C",
                    "Supply Fluid Under Temp Alarm Threshold",
                    "0",
                    "deg C",
                    "Supply Fluid Over Temp Warning Threshold",
                    "32",
                    "deg F",
                ]
            ]
        ]
    )


def test_discover(check_plugin: CheckPlugin, section: Mapping[str, tuple[float, str]]) -> None:
    assert list(check_plugin.discovery_function(section)) == [
        Service(item="Supply Fluid Temp Set Point 1"),
        Service(item="Supply Fluid Temp Set Point 2"),
    ]


@pytest.mark.parametrize(
    ["item", "params", "expected_result"],
    [
        pytest.param(
            "Supply Fluid Temp Set Point 1",
            {},
            [
                Result(
                    state=State.CRIT,
                    summary="14.0 °C (device warn/crit at 0.0/0.0 °C) (device warn/crit below 0.0/0.0 °C)",
                ),
                Metric("temp", 14.0, levels=(0.0, 0.0)),
            ],
            id="default params",
        ),
        pytest.param(
            "Supply Fluid Temp Set Point 2",
            {
                "levels": (20, 30),
                "device_levels_handling": "usr",
            },
            [
                Result(state=State.OK, summary="-6.0 °C"),
                Metric("temp", -6.0, levels=(20.0, 30.0)),
            ],
            id="custom thresholds",
        ),
    ],
)
def test_check(
    check_plugin: CheckPlugin,
    item: str,
    params: TempParamDict,
    section: Mapping[str, tuple[float, str]],
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_plugin.check_function(
                item=item,
                params=params,
                section=section,
            )
        )
        == expected_result
    )

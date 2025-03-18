#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from pathlib import Path

import pytest

from tests.unit.cmk.plugins.collection.agent_based.snmp import (
    get_parsed_snmp_section,
    snmp_is_detected,
)

from cmk.checkengine.checking import CheckPluginName

from cmk.base.api.agent_based.register import AgentBasedPlugins

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.dell_powerconnect.agent_based.dell_powerconnect_temp import (
    Section,
    snmp_section_dell_powerconnect_temp,
)

WALK = """
.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.674.10895
.1.3.6.1.4.1.89.53.15.1.9 42
.1.3.6.1.4.1.89.53.15.1.10 1
"""


def test_temp_parse(
    as_path: Callable[[str], Path],
) -> None:
    snmp_walk = as_path(WALK)

    assert snmp_is_detected(snmp_section_dell_powerconnect_temp, snmp_walk)

    assert get_parsed_snmp_section(snmp_section_dell_powerconnect_temp, snmp_walk) == Section(
        42.0, "OK"
    )


def test_temp_discover(agent_based_plugins: AgentBasedPlugins) -> None:
    plugin = agent_based_plugins.check_plugins[CheckPluginName("dell_powerconnect_temp")]
    assert (
        list(
            plugin.discovery_function(
                Section(42.0, "OK"),
            )
        )
    ) == [
        Service(item="Ambient"),
    ]


@pytest.mark.parametrize(
    "section, result",
    [
        (
            Section(None, "OK"),
            [
                Result(state=State.OK, summary="Status: OK"),
            ],
        ),
        (
            Section(41.0, "OK"),
            [
                Metric("temp", 41.0),
                Result(state=State.OK, summary="Temperature: 41.0 °C"),
                Result(state=State.OK, notice="State on device: OK"),
                Result(state=State.OK, notice="Configuration: only use device levels"),
            ],
        ),
        (
            Section(41.0, "unavailable"),
            [
                Metric("temp", 41.0),
                Result(state=State.OK, summary="Temperature: 41.0 °C"),
                Result(state=State.WARN, summary="State on device: unavailable"),
                Result(state=State.OK, notice="Configuration: only use device levels"),
            ],
        ),
        (
            Section(41.0, "non operational"),
            [
                Metric("temp", 41.0),
                Result(state=State.OK, summary="Temperature: 41.0 °C"),
                Result(state=State.CRIT, summary="State on device: non operational"),
                Result(state=State.OK, notice="Configuration: only use device levels"),
            ],
        ),
        (
            Section(41.0, "something"),
            [
                Metric("temp", 41.0),
                Result(state=State.OK, summary="Temperature: 41.0 °C"),
                Result(state=State.UNKNOWN, summary="State on device: something"),
                Result(state=State.OK, notice="Configuration: only use device levels"),
            ],
        ),
    ],
)
def test_temp_check(
    agent_based_plugins: AgentBasedPlugins, section: object, result: CheckResult
) -> None:
    plugin = agent_based_plugins.check_plugins[CheckPluginName("dell_powerconnect_temp")]

    assert (
        list(
            plugin.check_function(
                item="Ambient",
                params={"levels": (80, 90), "device_levels_handling": "dev"},
                section=section,
            )
        )
        == result
    )

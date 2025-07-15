#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from pathlib import Path

from cmk.agent_based.v2 import Result, Service, State
from cmk.checkengine.plugins import AgentBasedPlugins, CheckPluginName
from cmk.plugins.juniper.agent_based.juniper_fru_section import snmp_section_juniper_fru

from tests.unit.cmk.plugins.collection.agent_based.snmp import (
    get_parsed_snmp_section,
    snmp_is_detected,
)

# SUP-13184
DATA_0 = """
.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.2636.1.1.1.2.99
.1.3.6.1.4.1.2636.3.1.15.1.5.22.1.0.0 PSM 0
.1.3.6.1.4.1.2636.3.1.15.1.5.22.1.1.0 PSM 0 INP0
.1.3.6.1.4.1.2636.3.1.15.1.5.22.1.2.0 PSM 0 INP1
.1.3.6.1.4.1.2636.3.1.15.1.5.22.2.0.0 PSM 1
.1.3.6.1.4.1.2636.3.1.15.1.5.22.2.1.0 PSM 1 INP0
.1.3.6.1.4.1.2636.3.1.15.1.5.22.2.2.0 PSM 1 INP1
.1.3.6.1.4.1.2636.3.1.15.1.5.22.3.0.0 PSM 2
.1.3.6.1.4.1.2636.3.1.15.1.5.22.3.1.0 PSM 2 INP0
.1.3.6.1.4.1.2636.3.1.15.1.5.22.3.2.0 PSM 2 INP1
.1.3.6.1.4.1.2636.3.1.15.1.5.22.4.0.0 PSM 3
.1.3.6.1.4.1.2636.3.1.15.1.5.22.4.1.0 PSM 3 INP0
.1.3.6.1.4.1.2636.3.1.15.1.5.22.4.2.0 PSM 3 INP1
.1.3.6.1.4.1.2636.3.1.15.1.5.22.5.0.0 PSM 4
.1.3.6.1.4.1.2636.3.1.15.1.5.22.5.1.0 PSM 4 INP0
.1.3.6.1.4.1.2636.3.1.15.1.5.22.5.2.0 PSM 4 INP1
.1.3.6.1.4.1.2636.3.1.15.1.5.22.6.0.0 PSM 5
.1.3.6.1.4.1.2636.3.1.15.1.5.22.6.1.0 PSM 5 INP0
.1.3.6.1.4.1.2636.3.1.15.1.5.22.6.2.0 PSM 5 INP1
.1.3.6.1.4.1.2636.3.1.15.1.5.22.7.0.0 PSM 6
.1.3.6.1.4.1.2636.3.1.15.1.5.22.7.1.0 PSM 6 INP0
.1.3.6.1.4.1.2636.3.1.15.1.5.22.7.2.0 PSM 6 INP1
.1.3.6.1.4.1.2636.3.1.15.1.5.22.8.0.0 PSM 7
.1.3.6.1.4.1.2636.3.1.15.1.5.22.8.1.0 PSM 7 INP0
.1.3.6.1.4.1.2636.3.1.15.1.5.22.8.2.0 PSM 7 INP1
.1.3.6.1.4.1.2636.3.1.15.1.5.22.9.0.0 PSM 8
.1.3.6.1.4.1.2636.3.1.15.1.5.22.9.1.0 PSM 8 INP0
.1.3.6.1.4.1.2636.3.1.15.1.5.22.9.2.0 PSM 8 INP1
.1.3.6.1.4.1.2636.3.1.15.1.6.22.1.0.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.1.1.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.1.2.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.2.0.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.2.1.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.2.2.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.3.0.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.3.1.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.3.2.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.4.0.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.4.1.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.4.2.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.5.0.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.5.1.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.5.2.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.6.0.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.6.1.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.6.2.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.7.0.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.7.1.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.7.2.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.8.0.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.8.1.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.8.2.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.9.0.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.9.1.0 18
.1.3.6.1.4.1.2636.3.1.15.1.6.22.9.2.0 18
.1.3.6.1.4.1.2636.3.1.15.1.8.22.1.0.0 2
.1.3.6.1.4.1.2636.3.1.15.1.8.22.1.1.0 2
.1.3.6.1.4.1.2636.3.1.15.1.8.22.1.2.0 2
.1.3.6.1.4.1.2636.3.1.15.1.8.22.2.0.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.2.1.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.2.2.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.3.0.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.3.1.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.3.2.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.4.0.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.4.1.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.4.2.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.5.0.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.5.1.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.5.2.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.6.0.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.6.1.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.6.2.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.7.0.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.7.1.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.7.2.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.8.0.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.8.1.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.8.2.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.22.9.0.0 2
.1.3.6.1.4.1.2636.3.1.15.1.8.22.9.1.0 2
.1.3.6.1.4.1.2636.3.1.15.1.8.22.9.2.0 2
"""

# SUP-13184
DATA_1 = """
.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.2636.1.1.1.2.25
.1.3.6.1.4.1.2636.3.1.15.1.5.2.1.0.0 PEM 0
.1.3.6.1.4.1.2636.3.1.15.1.5.2.2.0.0 PEM 1
.1.3.6.1.4.1.2636.3.1.15.1.5.2.3.0.0 PEM 2
.1.3.6.1.4.1.2636.3.1.15.1.5.2.4.0.0 PEM 3
.1.3.6.1.4.1.2636.3.1.15.1.6.2.1.0.0 7
.1.3.6.1.4.1.2636.3.1.15.1.6.2.2.0.0 7
.1.3.6.1.4.1.2636.3.1.15.1.6.2.3.0.0 7
.1.3.6.1.4.1.2636.3.1.15.1.6.2.4.0.0 7
.1.3.6.1.4.1.2636.3.1.15.1.8.2.1.0.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.2.2.0.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.2.3.0.0 6
.1.3.6.1.4.1.2636.3.1.15.1.8.2.4.0.0 6
"""


def test_juniper_fru(
    agent_based_plugins: AgentBasedPlugins, as_path: Callable[[str], Path]
) -> None:
    assert snmp_is_detected(snmp_section_juniper_fru, as_path(DATA_1))
    plugin = agent_based_plugins.check_plugins[CheckPluginName("juniper_fru")]
    parsed = get_parsed_snmp_section(snmp_section_juniper_fru, as_path(DATA_1))
    assert list(plugin.discovery_function(parsed)) == [
        Service(item="PEM 0"),
        Service(item="PEM 1"),
        Service(item="PEM 2"),
        Service(item="PEM 3"),
    ]
    assert list(plugin.check_function(item="PEM 1", params={}, section=parsed)) == [
        Result(state=State.OK, summary="Operational status: online")
    ]


def test_juniper_fru_18(
    agent_based_plugins: AgentBasedPlugins, as_path: Callable[[str], Path]
) -> None:
    assert snmp_is_detected(snmp_section_juniper_fru, as_path(DATA_0))
    plugin = agent_based_plugins.check_plugins[CheckPluginName("juniper_fru")]
    parsed = get_parsed_snmp_section(snmp_section_juniper_fru, as_path(DATA_0))
    assert list(plugin.discovery_function(parsed)) == [
        Service(item="PSM 1"),
        Service(item="PSM 1 INP0"),
        Service(item="PSM 1 INP1"),
        Service(item="PSM 2"),
        Service(item="PSM 2 INP0"),
        Service(item="PSM 2 INP1"),
        Service(item="PSM 3"),
        Service(item="PSM 3 INP0"),
        Service(item="PSM 3 INP1"),
        Service(item="PSM 4"),
        Service(item="PSM 4 INP0"),
        Service(item="PSM 4 INP1"),
        Service(item="PSM 5"),
        Service(item="PSM 5 INP0"),
        Service(item="PSM 5 INP1"),
        Service(item="PSM 6"),
        Service(item="PSM 6 INP0"),
        Service(item="PSM 6 INP1"),
        Service(item="PSM 7"),
        Service(item="PSM 7 INP0"),
        Service(item="PSM 7 INP1"),
    ]
    assert list(plugin.check_function(item="PSM 1", params={}, section=parsed)) == [
        Result(state=State.OK, summary="Operational status: online")
    ]

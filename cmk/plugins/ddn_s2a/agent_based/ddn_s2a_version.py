#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.ddn_s2a.lib import parse_ddn_s2a_api_response

Section = Mapping[str, str]


def parse_ddn_s2a_version(string_table: StringTable) -> Section:
    return {key: value[0] for key, value in parse_ddn_s2a_api_response(string_table).items()}


def discover_ddn_s2a_version(section: Section) -> DiscoveryResult:
    yield Service()


def check_ddn_s2a_version(section: Section) -> CheckResult:
    yield Result(state=State.OK, summary=f"Platform: {section['platform']}")
    yield Result(
        state=State.OK,
        summary=f"Firmware Version: {section['fw_version']} ({section['fw_date']})",
    )
    yield Result(state=State.OK, summary=f"Bootrom Version: {section['bootrom_version']}")


agent_section_ddn_s2a_version = AgentSection(
    name="ddn_s2a_version",
    parse_function=parse_ddn_s2a_version,
)


check_plugin_ddn_s2a_version = CheckPlugin(
    name="ddn_s2a_version",
    service_name="DDN S2A Version",
    discovery_function=discover_ddn_s2a_version,
    check_function=check_ddn_s2a_version,
)

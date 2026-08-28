#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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


def parse_vnx_version(string_table: StringTable) -> StringTable:
    return string_table


agent_section_vnx_version = AgentSection(
    name="vnx_version",
    parse_function=parse_vnx_version,
)


def discover_vnx_version(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_vnx_version(section: StringTable) -> CheckResult:
    for line in section:
        yield Result(state=State.OK, summary=f"{line[0]}: {line[1]}")


check_plugin_vnx_version = CheckPlugin(
    name="vnx_version",
    service_name="VNX Version",
    discovery_function=discover_vnx_version,
    check_function=check_vnx_version,
)

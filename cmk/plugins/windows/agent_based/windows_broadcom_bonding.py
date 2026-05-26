#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<windows_broadcom_bonding>>>
# Caption            RedundancyStatus
# BOND_10.3          2
# BOND_HeartbeatMS   2
#


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


def parse_windows_broadcom_bonding(string_table: StringTable) -> StringTable:
    return string_table


def discover_windows_broadcom_bonding(section: StringTable) -> DiscoveryResult:
    for line in section[1:]:
        yield Service(item=" ".join(line[:-1]))


def check_windows_broadcom_bonding(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if " ".join(line[:-1]) == item:
            status = int(line[-1])
            if status == 5:
                yield Result(state=State.CRIT, summary="Bond not working")
                return
            if status == 4:
                yield Result(state=State.WARN, summary="Bond partly working")
                return
            if status == 2:
                yield Result(state=State.OK, summary="Bond fully working")
                return
            yield Result(state=State.UNKNOWN, summary="Bond status cannot be recognized")
            return
    yield Result(state=State.UNKNOWN, summary=f"Bond {item} not found in agent output")


agent_section_windows_broadcom_bonding = AgentSection(
    name="windows_broadcom_bonding",
    parse_function=parse_windows_broadcom_bonding,
)


check_plugin_windows_broadcom_bonding = CheckPlugin(
    name="windows_broadcom_bonding",
    service_name="Bonding Interface %s",
    discovery_function=discover_windows_broadcom_bonding,
    check_function=check_windows_broadcom_bonding,
)

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# cseSysMemoryUtilization   .1.3.6.1.4.1.9.9.305.1.1.2.0
#


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)


def discover_cisco_sys_mem(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_cisco_sys_mem(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    mem_used_percent = float(section[0][0])
    yield from check_levels(
        mem_used_percent,
        "mem_used_percent",
        params["levels"],
        human_readable_func=render.percent,
        infoname="Supervisor Memory used",
        boundaries=(0, 100),
    )


def parse_cisco_sys_mem(string_table: StringTable) -> StringTable | None:
    if not string_table or not string_table[0][0]:
        return None
    return string_table


snmp_section_cisco_sys_mem = SimpleSNMPSection(
    name="cisco_sys_mem",
    detect=startswith(".1.3.6.1.2.1.1.1.0", "Cisco NX-OS"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.305.1.1.2",
        oids=["0"],
    ),
    parse_function=parse_cisco_sys_mem,
)


check_plugin_cisco_sys_mem = CheckPlugin(
    name="cisco_sys_mem",
    service_name="Supervisor Mem Used",
    discovery_function=discover_cisco_sys_mem,
    check_function=check_cisco_sys_mem,
    check_ruleset_name="cisco_supervisor_mem",
    check_default_parameters={"levels": (80.0, 90.0)},
)

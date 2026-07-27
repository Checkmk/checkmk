#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# F5OS rSeries tenant instances
# MIB: F5-OS-TENANT-MIB (.1.3.6.1.4.1.12276.1.5)

from dataclasses import dataclass

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.f5os_rseries.lib.detect import DETECT_F5OS_RSERIES


@dataclass(frozen=True)
class F5OSTenant:
    name: str  # tenantInstanceName (item key)
    phase: str  # tenantInstancePhase (operational state)
    status: str  # tenantInstanceStatus (status message)


def parse_f5os_rseries_tenant(string_table: StringTable) -> dict[str, F5OSTenant]:
    result: dict[str, F5OSTenant] = {}
    for row in string_table:
        name = row[0].strip("\0")
        if not name:
            continue
        result[name] = F5OSTenant(
            name=name,
            phase=row[1].strip("\0"),
            status=row[2].strip("\0"),
        )
    return result


snmp_section_f5os_rseries_tenant = SimpleSNMPSection(
    name="f5os_rseries_tenant",
    parse_function=parse_f5os_rseries_tenant,
    detect=DETECT_F5OS_RSERIES,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12276.1.5.1.7.1.1",
        oids=[
            "3",  # tenantInstanceName (item key)
            "6",  # tenantInstancePhase (operational state string)
            "9",  # tenantInstanceStatus (status message string)
        ],
    ),
)


def discover_f5os_rseries_tenant(section: dict[str, F5OSTenant]) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_f5os_rseries_tenant(item: str, section: dict[str, F5OSTenant]) -> CheckResult:
    tenant = section.get(item)
    if tenant is None:
        return

    if tenant.phase == "Running":
        state = State.OK
    elif tenant.phase in ("Starting", "Stopping"):
        state = State.WARN
    else:
        state = State.CRIT

    yield Result(state=state, summary=f"State: {tenant.phase}")
    if tenant.status:
        yield Result(state=State.OK, notice=f"Status: {tenant.status}")


check_plugin_f5os_rseries_tenant = CheckPlugin(
    name="f5os_rseries_tenant",
    sections=["f5os_rseries_tenant"],
    service_name="F5OS Tenant %s",
    discovery_function=discover_f5os_rseries_tenant,
    check_function=check_f5os_rseries_tenant,
)

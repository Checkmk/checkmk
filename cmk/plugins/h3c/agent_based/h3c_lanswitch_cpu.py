#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# Example output of multi-unit stack (SS5500-EL, etc):
# SNMPv2-SMI::enterprises.43.45.1.6.1.1.1.3.65536 = Gauge32: 11
#
# Example outpout of multi-slot switche (SS8800 etc):
# SNMPv2-SMI::enterprises.43.45.1.6.1.1.1.3.0 = Gauge32: 11
# [...]
# SNMPv2-SMI::enterprises.43.45.1.6.1.1.1.3.12 = Gauge32: 16
# SNMPv2-SMI::enterprises.43.45.1.6.1.1.1.3.13 = Gauge32: 16


# We do not want to use the end OID as item since.
# We prefer "Switch 1 CPU 1" over "65537"...


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Metric,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def _genitem(item: str) -> str:
    # decide switch class here (stacked or standalone/modular)
    cpuid = int(item)

    # if we have a cpuid lower than (hopefully) 256 it is not hashed with a unit ID
    if cpuid < 256:
        switchid = 1
        cputype = "Slot"
        cpunum = cpuid

    # othwise, if above 64k it is a known stackable switch
    elif cpuid >= 65536:
        switchid = cpuid // 65536
        cputype = "CPU"
        cpunum = cpuid % 65536

    # if we end up here 3com has added another hash method.
    else:
        switchid = 1
        cputype = "Unknown"
        cpunum = cpuid
    return f"Switch {switchid} {cputype} {cpunum}"


def discover_h3c_lanswitch_cpu(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=_genitem(line[0]))


def check_h3c_lanswitch_cpu(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    warn, crit = params["levels"]
    for line in section:
        if _genitem(line[0]) == item:
            util = int(line[1])
            infotext = f"average usage was {util}% over last 5 minutes."

            if util > crit:
                yield Result(state=State.CRIT, summary=infotext)
            elif util > warn:
                yield Result(state=State.WARN, summary=infotext)
            else:
                yield Result(state=State.OK, summary=infotext)
            yield Metric("usage", util, levels=(warn, crit), boundaries=(0, 100))
            return

    yield Result(state=State.UNKNOWN, summary=f"{item} not found")


def parse_h3c_lanswitch_cpu(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_h3c_lanswitch_cpu = SimpleSNMPSection(
    name="h3c_lanswitch_cpu",
    detect=contains(".1.3.6.1.2.1.1.1.0", "3com s"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.43.45.1.6.1.1.1",
        oids=[OIDEnd(), "3"],
    ),
    parse_function=parse_h3c_lanswitch_cpu,
)


check_plugin_h3c_lanswitch_cpu = CheckPlugin(
    name="h3c_lanswitch_cpu",
    service_name="CPU Utilization %s",
    discovery_function=discover_h3c_lanswitch_cpu,
    check_function=check_h3c_lanswitch_cpu,
    check_default_parameters={"levels": (50, 75)},
)

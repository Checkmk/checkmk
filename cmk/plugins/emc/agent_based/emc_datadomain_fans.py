#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


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
from cmk.plugins.emc.lib import DETECT_DATADOMAIN


def discover_emc_datadomain_fans(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=f"{line[0]}-{line[1]}")


def check_emc_datadomain_fans(item: str, section: StringTable) -> CheckResult:
    state_table = {
        "0": ("notfound", State.WARN),
        "1": ("OK", State.OK),
        "2": ("Fail", State.CRIT),
    }
    fan_level = {"0": "Unknown", "1": "Low", "2": "Medium", "3": "High"}
    for line in section:
        if item == f"{line[0]}-{line[1]}":
            dev_descr = line[2]
            dev_level = line[3]
            dev_state = line[4]
            dev_state_str, dev_state_rc = state_table.get(dev_state, ("Unknown", State.UNKNOWN))
            dev_level_str = fan_level.get(dev_level, "Unknown")
            infotext = f"{dev_descr} {dev_state_str} RPM {dev_level_str}"
            yield Result(state=dev_state_rc, summary=infotext)
            return


def parse_emc_datadomain_fans(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_emc_datadomain_fans = SimpleSNMPSection(
    name="emc_datadomain_fans",
    detect=DETECT_DATADOMAIN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19746.1.1.3.1.1.1",
        oids=["1", "2", "4", "5", "6"],
    ),
    parse_function=parse_emc_datadomain_fans,
)


check_plugin_emc_datadomain_fans = CheckPlugin(
    name="emc_datadomain_fans",
    service_name="FAN %s",
    discovery_function=discover_emc_datadomain_fans,
    check_function=check_emc_datadomain_fans,
)

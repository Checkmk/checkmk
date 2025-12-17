#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.emc.lib import DETECT_DATADOMAIN


def discover_emc_datadomain_nvbat(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=f"{line[0]}-{line[1]}")


def check_emc_datadomain_nvbat(item: str, section: StringTable) -> CheckResult:
    state_table = {
        "0": ("OK", State.OK),
        "1": ("Disabled", State.WARN),
        "2": ("Discharged", State.CRIT),
        "3": ("Softdisabled", State.WARN),
    }
    for line in section:
        if item == f"{line[0]}-{line[1]}":
            dev_charge = line[3]
            dev_state = line[2]
            dev_state_str, dev_state_rc = state_table.get(dev_state, ("Unknown", State.UNKNOWN))
            yield Result(
                state=dev_state_rc, summary=f"Status {dev_state_str} Charge Level {dev_charge}%"
            )
            yield Metric("battery_capacity", float(dev_charge))
            return


def parse_emc_datadomain_nvbat(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_emc_datadomain_nvbat = SimpleSNMPSection(
    name="emc_datadomain_nvbat",
    detect=DETECT_DATADOMAIN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19746.1.2.3.1.1",
        oids=["1", "2", "3", "4"],
    ),
    parse_function=parse_emc_datadomain_nvbat,
)


check_plugin_emc_datadomain_nvbat = CheckPlugin(
    name="emc_datadomain_nvbat",
    service_name="NVRAM Battery %s",
    discovery_function=discover_emc_datadomain_nvbat,
    check_function=check_emc_datadomain_nvbat,
)

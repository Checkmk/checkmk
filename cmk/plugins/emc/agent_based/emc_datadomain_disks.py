#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.emc.lib import DETECT_DATADOMAIN


def discover_emc_datadomain_disks(section: Sequence[StringTable]) -> DiscoveryResult:
    for line in section[0]:
        yield Service(item=f"{line[0]}-{line[1]}")


def check_emc_datadomain_disks(item: str, section: Sequence[StringTable]) -> CheckResult:
    state_table = {
        "1": ("Operational", State.OK),
        "2": ("Unknown", State.UNKNOWN),
        "3": ("Absent", State.WARN),
        "4": ("Failed", State.CRIT),
        "5": ("Spare", State.OK),
        "6": ("Available", State.OK),
        "10": ("System", State.OK),
    }
    for line in section[0]:
        if item == line[0] + "-" + line[1]:
            model = line[2]
            firmware = line[3]
            serial = line[4]
            capacity = line[5]
            dev_state = line[6]
            dev_state_str, dev_state_rc = state_table.get(dev_state, ("Unknown", State.UNKNOWN))
            yield Result(state=dev_state_rc, summary=dev_state_str)
            index = int(line[7].split(".")[1]) - 1
            if len(section[1]) > index:
                busy = section[1][index][0]
                yield Result(state=State.OK, summary=f"busy {busy}%")
                yield Metric("busy", float(busy))
            yield Result(
                state=State.OK,
                summary=f"Model {model}, Firmware {firmware}, Serial {serial}, Capacity {capacity}",
            )


def parse_emc_datadomain_disks(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


snmp_section_emc_datadomain_disks = SNMPSection(
    name="emc_datadomain_disks",
    detect=DETECT_DATADOMAIN,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.19746.1.6.1.1.1",
            oids=["1", "2", "4", "5", "6", "7", "8", OIDEnd()],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.19746.1.6.2.1.1",
            oids=["6"],
        ),
    ],
    parse_function=parse_emc_datadomain_disks,
)


check_plugin_emc_datadomain_disks = CheckPlugin(
    name="emc_datadomain_disks",
    service_name="Hard Disk %s",
    discovery_function=discover_emc_datadomain_disks,
    check_function=check_emc_datadomain_disks,
)

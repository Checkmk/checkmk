#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


def bintec_brrp_status_compose_item(brrp_id):
    return re.sub(r"\..*", "", brrp_id)


def inventory_bintec_brrp_status(section: StringTable) -> DiscoveryResult:
    inventory = []
    for brrp_id, _brrp_status in section:
        inventory.append((bintec_brrp_status_compose_item(brrp_id), None))
    yield from [Service(item=item, parameters=parameters) for (item, parameters) in inventory]


def check_bintec_brrp_status(item: str, section: StringTable) -> CheckResult:
    for brrp_id, brrp_status in section:
        brrp_id = bintec_brrp_status_compose_item(brrp_id)
        if brrp_id == item:
            if brrp_status == "1":
                message = "Status for %s is initialize" % brrp_id
                status = State.WARN
            elif brrp_status == "2":
                message = "Status for %s is backup" % brrp_id
                status = State.OK
            elif brrp_status == "3":
                message = "Status for %s is master" % brrp_id
                status = State.OK
            else:
                message = f"Status for {brrp_id} is at unknown value {brrp_status}"
                status = State.UNKNOWN

            yield Result(state=status, summary=message)
            return

    yield Result(state=State.UNKNOWN, summary="Status for %s not found" % item)
    return


def parse_bintec_brrp_status(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_bintec_brrp_status = SimpleSNMPSection(
    name="bintec_brrp_status",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.272.4"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.272.4.40.1.1",
        oids=[OIDEnd(), "4"],
    ),
    parse_function=parse_bintec_brrp_status,
)
check_plugin_bintec_brrp_status = CheckPlugin(
    name="bintec_brrp_status",
    service_name="BRRP Status %s",
    discovery_function=inventory_bintec_brrp_status,
    check_function=check_bintec_brrp_status,
)

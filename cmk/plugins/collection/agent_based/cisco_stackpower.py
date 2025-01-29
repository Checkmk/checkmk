#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.9.9.500.1.3.2.1.2.1001.0 1
# .1.3.6.1.4.1.9.9.500.1.3.2.1.2.1001.1 1
# .1.3.6.1.4.1.9.9.500.1.3.2.1.2.2001.0 1
# .1.3.6.1.4.1.9.9.500.1.3.2.1.2.2001.1 1
# .1.3.6.1.4.1.9.9.500.1.3.2.1.2.3001.0 1
# .1.3.6.1.4.1.9.9.500.1.3.2.1.2.3001.1 1
# .1.3.6.1.4.1.9.9.500.1.3.2.1.3.1001.0 "00 00 00 00 00 00 "
# .1.3.6.1.4.1.9.9.500.1.3.2.1.3.1001.1 "00 00 00 00 00 00 "
# .1.3.6.1.4.1.9.9.500.1.3.2.1.3.2001.0 "00 00 00 00 00 00 "
# .1.3.6.1.4.1.9.9.500.1.3.2.1.3.2001.1 "00 00 00 00 00 00 "
# .1.3.6.1.4.1.9.9.500.1.3.2.1.3.3001.0 "00 00 00 00 00 00 "
# .1.3.6.1.4.1.9.9.500.1.3.2.1.3.3001.1 "00 00 00 00 00 00 "
# .1.3.6.1.4.1.9.9.500.1.3.2.1.4.1001.0 0
# .1.3.6.1.4.1.9.9.500.1.3.2.1.4.1001.1 0
# .1.3.6.1.4.1.9.9.500.1.3.2.1.4.2001.0 0
# .1.3.6.1.4.1.9.9.500.1.3.2.1.4.2001.1 0
# .1.3.6.1.4.1.9.9.500.1.3.2.1.4.3001.0 0
# .1.3.6.1.4.1.9.9.500.1.3.2.1.4.3001.1 0
# .1.3.6.1.4.1.9.9.500.1.3.2.1.5.1001.0 1
# .1.3.6.1.4.1.9.9.500.1.3.2.1.5.1001.1 1
# .1.3.6.1.4.1.9.9.500.1.3.2.1.5.2001.0 1
# .1.3.6.1.4.1.9.9.500.1.3.2.1.5.2001.1 1
# .1.3.6.1.4.1.9.9.500.1.3.2.1.5.3001.0 1
# .1.3.6.1.4.1.9.9.500.1.3.2.1.5.3001.1 1
# .1.3.6.1.4.1.9.9.500.1.3.2.1.6.1001.0 40
# .1.3.6.1.4.1.9.9.500.1.3.2.1.6.1001.1 40
# .1.3.6.1.4.1.9.9.500.1.3.2.1.6.2001.0 40
# .1.3.6.1.4.1.9.9.500.1.3.2.1.6.2001.1 40
# .1.3.6.1.4.1.9.9.500.1.3.2.1.6.3001.0 40
# .1.3.6.1.4.1.9.9.500.1.3.2.1.6.3001.1 40
# .1.3.6.1.4.1.9.9.500.1.3.2.1.7.1001.0 "Port 1"
# .1.3.6.1.4.1.9.9.500.1.3.2.1.7.1001.1 "Port 2"
# .1.3.6.1.4.1.9.9.500.1.3.2.1.7.2001.0 "Port 1"
# .1.3.6.1.4.1.9.9.500.1.3.2.1.7.2001.1 "Port 2"
# .1.3.6.1.4.1.9.9.500.1.3.2.1.7.3001.0 "Port 1"
# .1.3.6.1.4.1.9.9.500.1.3.2.1.7.3001.1 "Port 2"


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


def inventory_cisco_stackpower(section: StringTable) -> DiscoveryResult:
    yield from (
        Service(item="{} {}".format(oid.split(".")[0], port_name))
        for oid, port_oper_status, _port_link_status, port_name in section
        if port_oper_status == "1"
    )


def check_cisco_stackpower(item: str, section: StringTable) -> CheckResult:
    map_oper_status = {
        "1": Result(state=State.OK, summary="Port enabled"),
        "2": Result(state=State.CRIT, summary="Port disabled"),
    }

    map_status = {
        "1": Result(state=State.OK, summary="Status: connected and operational"),
        "2": Result(state=State.CRIT, summary="Status: forced down or not connected"),
    }

    for oid, port_oper_status, port_link_status, port_name in section:
        if item == "{} {}".format(oid.split(".")[0], port_name):
            yield map_oper_status[port_oper_status]
            yield map_status[port_link_status]


def parse_cisco_stackpower(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_cisco_stackpower = SimpleSNMPSection(
    name="cisco_stackpower",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.516"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.500.1.3.2.1",
        oids=[OIDEnd(), "2", "5", "7"],
    ),
    parse_function=parse_cisco_stackpower,
)
check_plugin_cisco_stackpower = CheckPlugin(
    name="cisco_stackpower",
    service_name="Stackpower Interface %s",
    discovery_function=inventory_cisco_stackpower,
    check_function=check_cisco_stackpower,
)

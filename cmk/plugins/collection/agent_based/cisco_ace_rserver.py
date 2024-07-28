#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# Parse an InetAddress type object as defined in the SNMP-FRAMEWORK-MIB


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    Metric,
    OIDBytes,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def parse_framework_mib_inet_address(ip_address_type, ip_address):
    if ip_address_type == 1:
        return "%d.%d.%d.%d" % tuple(ip_address)
    if ip_address_type == 2:
        return "%x:%x:%x:%x:%x:%x:%x:%x" % tuple(ip_address)
    if ip_address_type == 3:
        return "%d.%d.%d.%d%%%d%d%d%d" % tuple(ip_address)
    if ip_address_type == 4:
        return "%x:%x:%x:%x:%x:%x:%x:%x%%%d%d%d%d" % tuple(ip_address)
    if ip_address_type == 5:  # Means DNS name - Reconvert to ASCII string
        return "".join([chr(x) for x in ip_address])
    if ip_address_type == 0:  # Unknown address type - represent as hex string
        return "".join(["%x" % byte for byte in ip_address])
    return None


def inventory_cisco_ace_rserver(section: StringTable) -> DiscoveryResult:
    for name, ip_address_type, ip_address, descr, _admin_status, _oper_status, _conns in section:
        ip = parse_framework_mib_inet_address(int(ip_address_type), ip_address)
        if name != "":
            item = name
        elif descr != "":
            item = descr
        else:
            item = ip
        yield Service(item=item)


def check_cisco_ace_rserver(item: str, section: StringTable) -> CheckResult:
    admin_stati = {
        "1": "in service",
        "2": "out of service",
        "3": "in service, standby",
    }
    oper_stati = {
        "1": (State.CRIT, "out of service"),
        "2": (State.OK, "in service"),
        "3": (State.CRIT, "failed"),
        "4": (State.CRIT, "ready to test"),
        "5": (State.CRIT, "testing"),
        "6": (State.CRIT, "max connection reached, throttling"),
        "7": (State.CRIT, "max clients reached, throttling"),
        "8": (State.CRIT, "dfp throttle"),
        "9": (State.CRIT, "probe failed"),
        "10": (State.WARN, "probe testing"),
        "11": (State.CRIT, "oper wait"),
        "12": (State.CRIT, "test wait"),
        "13": (State.CRIT, "inband probe failed"),
        "14": (State.CRIT, "return code failed"),
        "15": (State.CRIT, "arp failed"),
        "16": (State.WARN, "standby"),
        "17": (State.CRIT, "inactive"),
        "18": (State.CRIT, "max load reached"),
    }

    for name, ip_address_type, ip_address, descr, admin_status, oper_status, conns in section:
        ip_addr = parse_framework_mib_inet_address(ip_address_type, ip_address)
        if item in {name, ip_addr, descr}:
            admin_state = admin_stati[admin_status]
            state, state_txt = oper_stati[oper_status]
            if admin_status == "2" and state is State.CRIT:
                state = State.WARN  # max state is WARN if real server out of service
            infotext = f"Operational State: {state_txt}, Administrative State: {admin_state}, Current Connections: {conns}"
            yield Metric("connections", int(conns))
            yield Result(state=state, summary=infotext)
            return


def parse_cisco_ace_rserver(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_cisco_ace_rserver = SimpleSNMPSection(
    name="cisco_ace_rserver",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.824"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.470.1.1.1.1",
        oids=["1", "3", OIDBytes("4"), "5", "12", "13", "19"],
    ),
    parse_function=parse_cisco_ace_rserver,
)


check_plugin_cisco_ace_rserver = CheckPlugin(
    name="cisco_ace_rserver",
    service_name="ACE RServer %s",
    discovery_function=inventory_cisco_ace_rserver,
    check_function=check_cisco_ace_rserver,
)

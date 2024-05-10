#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# Parse an InetAddress type object as defined in the SNMP-FRAMEWORK-MIB


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import equals, OIDBytes, SNMPTree, StringTable


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


def inventory_cisco_ace_rserver(info):
    for name, ip_address_type, ip_address, descr, _admin_status, _oper_status, _conns in info:
        ip = parse_framework_mib_inet_address(int(ip_address_type), ip_address)
        if name != "":
            item = name
        elif descr != "":
            item = descr
        else:
            item = ip
        yield item, None


def check_cisco_ace_rserver(item, _no_params, info):
    admin_stati = {
        "1": "in service",
        "2": "out of service",
        "3": "in service, standby",
    }
    oper_stati = {
        "1": (2, "out of service"),
        "2": (0, "in service"),
        "3": (2, "failed"),
        "4": (2, "ready to test"),
        "5": (2, "testing"),
        "6": (2, "max connection reached, throttling"),
        "7": (2, "max clients reached, throttling"),
        "8": (2, "dfp throttle"),
        "9": (2, "probe failed"),
        "10": (1, "probe testing"),
        "11": (2, "oper wait"),
        "12": (2, "test wait"),
        "13": (2, "inband probe failed"),
        "14": (2, "return code failed"),
        "15": (2, "arp failed"),
        "16": (1, "standby"),
        "17": (2, "inactive"),
        "18": (2, "max load reached"),
    }

    for name, ip_address_type, ip_address, descr, admin_status, oper_status, conns in info:
        ip_addr = parse_framework_mib_inet_address(ip_address_type, ip_address)
        if item in {name, ip_addr, descr}:
            admin_state = admin_stati[admin_status]
            state, state_txt = oper_stati[oper_status]
            if admin_status == "2" and state == 2:
                state = 1  # max state is WARN if real server out of service
            infotext = f"Operational State: {state_txt}, Administrative State: {admin_state}, Current Connections: {conns}"
            perfdata = [("connections", int(conns))]

            return state, infotext, perfdata
    return None


def parse_cisco_ace_rserver(string_table: StringTable) -> StringTable:
    return string_table


check_info["cisco_ace_rserver"] = LegacyCheckDefinition(
    parse_function=parse_cisco_ace_rserver,
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.824"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.470.1.1.1.1",
        oids=["1", "3", OIDBytes("4"), "5", "12", "13", "19"],
    ),
    service_name="ACE RServer %s",
    discovery_function=inventory_cisco_ace_rserver,
    check_function=check_cisco_ace_rserver,
)

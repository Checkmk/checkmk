#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import ipaddress
from collections.abc import Mapping, Sequence

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, contains, exists, OIDEnd, SNMPTree, StringTable

check_info = {}


def hex2ip(hexstr):
    """
    Converts a hex string (with or without spaces) to an IP address.
    Supports both IPv4 and IPv6.

    Examples:
        "C0 A8 01 01" => "192.168.1.1"
        "20 01 0D B8 00 00 00 00 00 00 00 00 00 00 00 01" => "2001:db8::1"
    """
    return str(ipaddress.ip_address(bytes.fromhex(hexstr.replace(" ", ""))))


def inventory_keepalived(section):
    for vrrp_id in section:
        yield vrrp_id, None


def check_keepalived(item, params, section):
    map_state = {
        "0": "init",
        "1": "backup",
        "2": "master",
        "3": "fault",
        "4": "unknown",
    }
    if item not in section:
        yield 3, "Item not found in output"
        return

    state, addresses = section[item]
    state_name = map_state[state]
    infotext = f"This node is {state_name}."
    if addresses:
        infotext += f" IP Address: {', '.join(addresses)}"
    yield params[state_name], infotext


def parse_keepalived(string_table: Sequence[StringTable]) -> Mapping[str, tuple[str, list[str]]]:
    """Map each VRRP instance id to its state and configured virtual IP addresses.

    The instance table (vrrpInstanceTable) and the address table (vrrpAddressTable) are
    indexed independently in the keepalived MIB: an instance can have zero, one, or several
    addresses. They are correlated here via the instance index (OIDEnd), not by row position,
    since a vrrp_instance without any configured VIP leaves the address table without a
    matching row for it.
    """
    instance_table, address_table = string_table

    addresses_by_instance: dict[str, list[str]] = {}
    for oid_end, address in address_table:
        instance_index = oid_end.split(".")[0]
        hexaddr = address.encode("latin-1").hex()
        addresses_by_instance.setdefault(instance_index, []).append(hex2ip(hexaddr))

    return {
        vrrp_id: (state, addresses_by_instance.get(instance_index, []))
        for vrrp_id, state, instance_index in instance_table
    }


check_info["keepalived"] = LegacyCheckDefinition(
    name="keepalived",
    parse_function=parse_keepalived,
    detect=all_of(contains(".1.3.6.1.2.1.1.1.0", "linux"), exists(".1.3.6.1.4.1.9586.100.5.1.1.0")),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9586.100.5.2.3.1",
            oids=["2", "4", OIDEnd()],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9586.100.5.2.6.1",
            oids=[OIDEnd(), "3"],
        ),
    ],
    service_name="VRRP Instance %s",
    discovery_function=inventory_keepalived,
    check_function=check_keepalived,
    check_ruleset_name="keepalived",
    check_default_parameters={
        "master": 0,
        "unknown": 3,
        "init": 0,
        "backup": 0,
        "fault": 2,
    },
)

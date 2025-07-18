#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import ipaddress
from collections.abc import Sequence

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import all_of, contains, exists, SNMPTree, StringTable


def hex2ip(hexstr):
    """
    Converts a hex string (with or without spaces) to an IP address.
    Supports both IPv4 and IPv6.

    Examples:
        "C0 A8 01 01" => "192.168.1.1"
        "20 01 0D B8 00 00 00 00 00 00 00 00 00 00 00 01" => "2001:db8::1"
    """
    return str(ipaddress.ip_address(bytes.fromhex(hexstr.replace(" ", ""))))


def inventory_keepalived(info):
    for entry in info[0]:
        vrrp_id = entry[0]
        yield vrrp_id, None


def check_keepalived(item, params, info):
    map_state = {
        "0": "init",
        "1": "backup",
        "2": "master",
        "3": "fault",
        "4": "unknown",
    }
    status = 3
    infotext = "Item not found in output"
    for id_, entry in enumerate(info[0]):
        vrrp_id = entry[0]
        address = info[1][id_][0]
        hexaddr = address.encode("latin-1").hex()
        if vrrp_id == item:
            status = params[map_state[str(entry[1])]]
            infotext = "This node is {}. IP Address: {}".format(
                map_state[str(entry[1])],
                hex2ip(hexaddr),
            )
    yield int(status), infotext


def parse_keepalived(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


check_info["keepalived"] = LegacyCheckDefinition(
    parse_function=parse_keepalived,
    detect=all_of(contains(".1.3.6.1.2.1.1.1.0", "linux"), exists(".1.3.6.1.4.1.9586.100.5.1.1.0")),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9586.100.5.2.3.1",
            oids=["2", "4"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9586.100.5.2.6.1",
            oids=["3"],
        ),
    ],
    service_name="VRRP Instance %s",
    discovery_function=inventory_keepalived,
    check_function=check_keepalived,
    check_ruleset_name="keepalived",
    check_default_parameters={
        "master": "0",
        "unknown": "3",
        "init": "0",
        "backup": "0",
        "fault": "2",
    },
)

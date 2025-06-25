#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    exists,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def hex2ip(hexstr: str) -> str:
    """
    Can parse strings in this form:
    17 20 16 00 00 01
    """
    hexstr = hexstr.replace(" ", "")
    blocks = ("".join(block) for block in zip(*[iter(hexstr)] * 2))
    int_blocks = (int(block, 16) for block in blocks)
    return ".".join(str(block) for block in int_blocks)


def inventory_keepalived(section: Sequence[StringTable]) -> DiscoveryResult:
    for entry in section[0]:
        vrrp_id = entry[0]
        yield Service(item=vrrp_id)


def check_keepalived(
    item: str, params: Mapping[str, Any], section: Sequence[StringTable]
) -> CheckResult:
    map_state = {
        "0": "init",
        "1": "backup",
        "2": "master",
        "3": "fault",
        "4": "unknown",
    }
    status = State.UNKNOWN
    infotext = "Item not found in output"
    for id_, entry in enumerate(section[0]):
        vrrp_id = entry[0]
        address = section[1][id_][0]
        hexaddr = address.encode("latin-1").hex()
        if vrrp_id == item:
            status = State(params[map_state[str(entry[1])]])
            infotext = f"This node is {map_state[str(entry[1])]}. IP Address: {hex2ip(hexaddr)}"
    yield Result(state=status, summary=infotext)


def parse_keepalived(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


snmp_section_keepalived = SNMPSection(
    name="keepalived",
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
    parse_function=parse_keepalived,
)


check_plugin_keepalived = CheckPlugin(
    name="keepalived",
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

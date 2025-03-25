#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDBytes, SNMPTree
from cmk.plugins.lib.ip_format import clean_v4_address, clean_v6_address
from cmk.plugins.lib.juniper import DETECT_JUNIPER

check_info = {}


def juniper_bgp_state_create_item(peering_entry):
    try:
        if len(peering_entry) == 4:
            return clean_v4_address(peering_entry)
        if len(peering_entry) == 16:
            return clean_v6_address(peering_entry)
    except (ValueError, IndexError):
        pass
    return " ".join("%02X" % int(i) for i in peering_entry)  # that's what has been in the data


def parse_juniper_bgp_state(string_table):
    bgp_state_map = {
        "0": "undefined",  # 0 does not exist
        "1": "idle",  # 1
        "2": "connect",  # 2
        "3": "active",  # 3
        "4": "opensent",  # 4
        "5": "openconfirm",  # 5
        "6": "established",  # 6
    }
    bgp_operational_state_map = {
        "0": "undefined",  # 0 does not exist
        "1": "halted",  # 1
        "2": "running",  # 2
    }
    parsed = {}
    for state, operational_state, peering_entry in string_table:
        item = juniper_bgp_state_create_item(peering_entry)
        state_txt = bgp_state_map.get(state.strip(), "undefined")
        operational_txt = bgp_operational_state_map.get(operational_state.strip(), "undefined")

        parsed[item] = {
            "state": state_txt,
            "operational_state": operational_txt,
        }
    return parsed


def check_juniper_bgp_state(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    state = data.get("state", "undefined")
    operational_state = data.get("operational_state", "undefined")

    status = {
        "established": 0,
        "undefined": 3,
    }.get(state, 2)
    # if we're halted, being un-established is fine
    yield (
        status if operational_state == "running" else 0,
        f"Status with peer {item} is {state}",
    )

    op_status = {
        "running": 0,
        "undefined": 3,
    }.get(operational_state, 1)
    yield op_status, "operational status: %s" % operational_state


def discover_juniper_bgp_state(section):
    yield from ((item, {}) for item in section)


check_info["juniper_bgp_state"] = LegacyCheckDefinition(
    name="juniper_bgp_state",
    detect=DETECT_JUNIPER,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2636.5.1.1.2.1.1.1",
        oids=["2", "3", OIDBytes("11")],
    ),
    parse_function=parse_juniper_bgp_state,
    service_name="BGP Status Peer %s",
    discovery_function=discover_juniper_bgp_state,
    check_function=check_juniper_bgp_state,
)

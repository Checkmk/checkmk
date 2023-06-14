#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover, get_parsed_item_data, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDBytes, SNMPTree
from cmk.base.plugins.agent_based.utils.ip_format import clean_v4_address, clean_v6_address
from cmk.base.plugins.agent_based.utils.juniper import DETECT_JUNIPER


def juniper_bgp_state_create_item(peering_entry):
    try:
        if len(peering_entry) == 4:
            return clean_v4_address(peering_entry)
        if len(peering_entry) == 16:
            return clean_v6_address(peering_entry)
    except (ValueError, IndexError):
        pass
    return " ".join("%02X" % int(i) for i in peering_entry)  # that's what has been in the data


def parse_juniper_bgp_state(info):
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
    for state, operational_state, peering_entry in info:
        item = juniper_bgp_state_create_item(peering_entry)
        state_txt = bgp_state_map.get(state.strip(), "undefined")
        operational_txt = bgp_operational_state_map.get(operational_state.strip(), "undefined")

        parsed[item] = {
            "state": state_txt,
            "operational_state": operational_txt,
        }
    return parsed


@get_parsed_item_data
def check_juniper_bgp_state(item, _no_params, data):
    state = data.get("state", "undefined")
    operational_state = data.get("operational_state", "undefined")

    status = {
        "established": 0,
        "undefined": 3,
    }.get(state, 2)
    # if we're halted, being un-established is fine
    yield status if operational_state == "running" else 0, "Status with peer %s is %s" % (
        item,
        state,
    )

    op_status = {
        "running": 0,
        "undefined": 3,
    }.get(operational_state, 1)
    yield op_status, "operational status: %s" % operational_state


check_info["juniper_bgp_state"] = LegacyCheckDefinition(
    detect=DETECT_JUNIPER,
    parse_function=parse_juniper_bgp_state,
    check_function=check_juniper_bgp_state,
    discovery_function=discover(),
    service_name="BGP Status Peer %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2636.5.1.1.2.1.1.1",
        oids=["2", "3", OIDBytes("11")],
    ),
)

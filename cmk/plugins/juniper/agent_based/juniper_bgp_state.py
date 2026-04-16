#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import TypedDict

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDBytes,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.juniper.lib import DETECT_JUNIPER
from cmk.plugins.lib.ip_format import clean_v4_address, clean_v6_address


class StateDict(TypedDict):
    state: str
    operational_state: str


Section = Mapping[str, StateDict]


def juniper_bgp_state_create_item(peering_entry: str) -> str:
    try:
        if len(peering_entry) == 4:
            return clean_v4_address(peering_entry)
        if len(peering_entry) == 16:
            return clean_v6_address(peering_entry)
    except (ValueError, IndexError):
        pass
    return " ".join("%02X" % int(i) for i in peering_entry)  # that's what has been in the data


def parse_juniper_bgp_state(string_table: StringTable) -> Section:
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
    parsed: dict[str, StateDict] = {}
    for state, operational_state, peering_entry in string_table:
        item = juniper_bgp_state_create_item(peering_entry)
        state_txt = bgp_state_map.get(state.strip(), "undefined")
        operational_txt = bgp_operational_state_map.get(operational_state.strip(), "undefined")

        parsed[item] = {
            "state": state_txt,
            "operational_state": operational_txt,
        }
    return parsed


def check_juniper_bgp_state(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    state = data.get("state", "undefined")
    operational_state = data.get("operational_state", "undefined")

    status = {
        "established": State.OK,
        "undefined": State.UNKNOWN,
    }.get(state, State.CRIT)
    # if we're halted, being un-established is fine
    yield Result(
        state=status if operational_state == "running" else State.OK,
        summary=f"Status with peer {item} is {state}",
    )

    op_status = {
        "running": State.OK,
        "undefined": State.UNKNOWN,
    }.get(operational_state, State.WARN)
    yield Result(state=op_status, summary="operational status: %s" % operational_state)


def discover_juniper_bgp_state(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


snmp_section_juniper_bgp_state = SimpleSNMPSection(
    name="juniper_bgp_state",
    detect=DETECT_JUNIPER,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2636.5.1.1.2.1.1.1",
        oids=["2", "3", OIDBytes("11")],
    ),
    parse_function=parse_juniper_bgp_state,
)

check_plugin_juniper_bgp_state = CheckPlugin(
    name="juniper_bgp_state",
    service_name="BGP Status Peer %s",
    discovery_function=discover_juniper_bgp_state,
    check_function=check_juniper_bgp_state,
)

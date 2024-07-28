#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.9.9.176.1.1.1.0   0  --> CISCO-RF-MIB::cRFStatusUnitId.0
# .1.3.6.1.4.1.9.9.176.1.1.2.0   14 --> CISCO-RF-MIB::cRFStatusUnitState.0
# .1.3.6.1.4.1.9.9.176.1.1.3.0   0  --> CISCO-RF-MIB::cRFStatusPeerUnitId.0
# .1.3.6.1.4.1.9.9.176.1.1.4.0   2  --> CISCO-RF-MIB::cRFStatusPeerUnitState.0
# .1.3.6.1.4.1.9.9.176.1.1.6.0   2  --> CISCO-RF-MIB::cRFStatusDuplexMode.0
# .1.3.6.1.4.1.9.9.176.1.1.8.0   1  --> CISCO-RF-MIB::cRFStatusLastSwactReasonCode.0

from collections.abc import Mapping
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
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def inventory_cisco_redundancy(section: StringTable) -> DiscoveryResult:
    try:
        swact_reason = section[0][5]
    except IndexError:
        pass
    else:
        if swact_reason != "1":
            yield Service(parameters={"init_states": section[0][:5]})


def check_cisco_redundancy(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    map_states = {
        "unit_state": {
            "0": "not found",
            "1": "not known",
            "2": "disabled",
            "3": "initialization",
            "4": "negotiation",
            "5": "standby cold",
            "6": "standby cold config",
            "7": "standby cold file sys",
            "8": "standby cold bulk",
            "9": "standby hot",
            "10": "active fast",
            "11": "active drain",
            "12": "active pre-config",
            "13": "active post-config",
            "14": "active",
            "15": "active extra load",
            "16": "active handback",
        },
        "duplex_mode": {
            "2": "False (SUB-Peer not detected)",
            "1": "True (SUB-Peer detected)",
        },
        "swact_reason": {
            "1": "unsupported",
            "2": "none",
            "3": "not known",
            "4": "user initiated",
            "5": "user forced",
            "6": "active unit failed",
            "7": "active unit removed",
            "8": "active lost gateway connectivity",
            "9": "RMI port went down on active",
        },
    }

    infotexts = {}
    for what, states in [("now", section[0][:5]), ("init", params["init_states"])]:
        unit_id, unit_state, peer_id, peer_state, duplex_mode = states
        infotexts[what] = "Unit ID: {} ({}), Peer ID: {} ({}), Duplex mode: {}".format(
            unit_id,
            map_states["unit_state"][unit_state],
            peer_id,
            map_states["unit_state"][peer_state],
            map_states["duplex_mode"][duplex_mode],
        )

    unit_id, unit_state, peer_id, peer_state, duplex_mode, _swact_reason = section[0]

    if params["init_states"] == section[0][:5]:
        state = State.OK
        infotext = "{}, Last swact reason code: {}".format(
            infotexts["now"],
            map_states["swact_reason"][section[0][5]],
        )
    else:
        if unit_state in ["2", "9", "14"] or peer_state in ["2", "9", "14"]:
            state = State.WARN
        else:
            state = State.CRIT

        infotext = "Switchover - Old status: {}, New status: {}".format(
            infotexts["init"],
            infotexts["now"],
        )

    if peer_state == "1":
        state = State.CRIT

    yield Result(state=state, summary=infotext)


def parse_cisco_redundancy(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_cisco_redundancy = SimpleSNMPSection(
    name="cisco_redundancy",
    detect=all_of(contains(".1.3.6.1.2.1.1.1.0", "cisco"), exists(".1.3.6.1.4.1.9.9.176.1.1.*")),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.176.1.1",
        oids=[
            "1",  # cRFStatusUnitId
            "2",  # cRFStatusUnitState
            "3",  # cRFStatusPeerUnitId
            "4",  # cRFStatusPeerUnitState
            "6",  # cRFStatusDuplexMode
            "8",  # cRFStatusLastSwactReasonCode
        ],
    ),
    parse_function=parse_cisco_redundancy,
)
check_plugin_cisco_redundancy = CheckPlugin(
    name="cisco_redundancy",
    service_name="Redundancy Framework Status",
    discovery_function=inventory_cisco_redundancy,
    check_function=check_cisco_redundancy,
    check_default_parameters={},
)

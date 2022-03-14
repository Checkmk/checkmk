#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.2.4  'Failover LAN Interface'
# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.2.6  'Primary unit (this device)'
# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.2.7  'Secondary unit'
# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.3.4  2
# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.3.6  9     < These two values flip during
# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.3.7  10    < failover
# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.4.4  'LAN_FO GigabitEthernet0/0.777'
# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.4.6  'Active unit'
# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.4.7  'Standby unit'

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    any_of,
    contains,
    register,
    Result,
    Service,
    SNMPTree,
    startswith,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)


@dataclass
class Section:
    local_role: str
    local_status: str
    local_status_detail: str
    failover_link_status: str
    failover_link_name: str
    remote_status: str


def parse_cisco_asa_failover(string_table: StringTable) -> Optional[Section]:
    failover = {}
    for role, status, detail in string_table:
        if "this device" in role and detail.lower() != "failover off":
            failover["local_role"] = role.split(" ")[0].lower()
            failover["local_status"] = status
            failover["local_status_detail"] = detail
        elif "failover" in role.lower():
            failover["failover_link_status"] = status
            failover["failover_link_name"] = detail
        else:
            failover["remote_status"] = status

    try:
        return Section(
            local_role=failover["local_role"],
            local_status=failover["local_status"],
            local_status_detail=failover["local_status_detail"],
            failover_link_status=failover["failover_link_status"],
            failover_link_name=failover["failover_link_name"],
            remote_status=failover["remote_status"],
        )
    except KeyError:
        return None


def discovery_cisco_asa_failover(section: Section) -> DiscoveryResult:
    yield Service()


_STATE_NAMES = {
    "1": "other",
    "2": "up",
    "3": "down",
    "4": "error",
    "5": "overTemp",
    "6": "busy",
    "7": "noMedia",
    "8": "backup",
    "9": "active",
    "10": "standby",
}


def _get_cisco_asa_state_name(st: str) -> str:
    return _STATE_NAMES.get(
        st,
        f"unknown {st}",
    )


def check_cisco_asa_failover(params: (Mapping[str, Any]), section: Section) -> CheckResult:
    yield Result(
        state=State.OK,
        summary=f"Device ({section.local_role}) is the {section.local_status_detail}",
    )

    if params[section.local_role] != _get_cisco_asa_state_name(section.local_status):
        yield Result(
            state=State(params["failover_state"]),
            summary=f"(The {section.local_role} device should be {params[section.local_role]})",
        )

    if section.local_status not in ["9", "10"]:  # local not active/standby
        yield Result(
            state=State(params["not_active_standby_state"]),
            summary=f"Unhandled state {_get_cisco_asa_state_name(section.local_status)} reported",
        )

    if section.remote_status not in ["9", "10"]:  # remote not active/standby
        yield Result(
            state=State(params["not_active_standby_state"]),
            summary=(
                f"Unhandled state {_get_cisco_asa_state_name(section.remote_status)} for "
                "remote device reported"
            ),
        )

    if section.failover_link_status != "2":  # not up
        yield Result(
            state=State(params["failover_link_state"]),
            summary=(
                f"Failover link {section.failover_link_name} state is "
                f"{_get_cisco_asa_state_name(section.failover_link_status)}"
            ),
        )


register.snmp_section(
    name="cisco_asa_failover",
    parse_function=parse_cisco_asa_failover,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.147.1.2.1.1.1",  # CISCO-FIREWALL-MIB::cfwHardwareStatusEntry
        oids=[
            "2",  # CISCO-FIREWALL-MIB::cfwHardwareInformation
            "3",  # CISCO-FIREWALL-MIB::cfwHardwareStatusValue
            "4",  # CISCO-FIREWALL-MIB::cfwHardwareStatusDetail
        ],
    ),
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.1.0", "cisco adaptive security"),
        contains(".1.3.6.1.2.1.1.1.0", "cisco pix security"),
        startswith(".1.3.6.1.2.1.1.1.0", "cisco firepower threat defense"),
    ),
)

register.check_plugin(
    name="cisco_asa_failover",
    service_name="Failover state",
    discovery_function=discovery_cisco_asa_failover,
    check_function=check_cisco_asa_failover,
    check_default_parameters={
        "primary": "active",
        "secondary": "standby",
        "failover_state": 1,
        "failover_link_state": 2,
        "not_active_standby_state": 1,
    },
    check_ruleset_name="cisco_asa_failover",
)

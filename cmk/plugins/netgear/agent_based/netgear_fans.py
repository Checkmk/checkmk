#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.fan import check_fan
from cmk.plugins.netgear.lib import DETECT_NETGEAR

# .1.3.6.1.4.1.4526.10.43.1.6.1.3.1.0 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.1.0
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.1.1 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.1.1
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.1.2 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.1.2
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.1.3 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.1.3
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.1.4 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.1.4
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.1.5 1 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.1.5
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.2.0 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.2.0
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.2.1 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.2.1
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.2.2 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.2.2
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.2.3 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.2.3
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.2.4 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.2.4
# .1.3.6.1.4.1.4526.10.43.1.6.1.3.2.5 1 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanItemState.2.5
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.1.0 3950 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.1.0
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.1.1 3700 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.1.1
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.1.2 3600 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.1.2
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.1.3 3400 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.1.3
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.1.4 0 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.1.4
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.1.5 0 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.1.5
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.2.0 3650 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.2.0
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.2.1 3400 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.2.1
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.2.2 3300 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.2.2
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.2.3 3500 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.2.3
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.2.4 0 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.2.4
# .1.3.6.1.4.1.4526.10.43.1.6.1.4.2.5 0 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesFanSpeed.2.5

# Just assumed


@dataclass(frozen=True)
class Fan:
    state: str
    reading_str: str


@dataclass(frozen=True)
class Section:
    version: str
    fans: Mapping[str, Fan]


def netgear_map_state_txt_to_state(state_nr: str, version: str) -> tuple[State, str]:
    map_state_txt_to_state = {
        "operational": State.OK,
        "failed": State.CRIT,
        "powering": State.OK,
        "not powering": State.WARN,
        "not present": State.WARN,
        "no power": State.CRIT,
        "incompatible": State.CRIT,
    }

    if version.startswith("8."):
        map_states = {
            "1": "operational",
            "2": "failed",
            "3": "powering",
            "4": "not powering",
            "5": "not present",
        }
    elif version.startswith("10."):
        map_states = {
            "1": "notpresent",
            "2": "operational",
            "3": "failed",
            "4": "powering",
            "5": "no power",
            "6": "not powering",
            "7": "incompatible",
        }
    else:
        map_states = {
            "1": "not present",
            "2": "operational",
            "3": "failed",
        }

    state_txt = map_states.get(state_nr, f"unknown({state_nr})")
    return map_state_txt_to_state.get(state_txt, State.UNKNOWN), state_txt


def parse_netgear_fans(string_table: Sequence[StringTable]) -> Section:
    versioninfo, sensorinfo = string_table
    fans: dict[str, Fan] = {}
    for oid_end, sstate, reading_str in sensorinfo:
        fans.setdefault(
            oid_end.replace(".", "/"),
            Fan(state=sstate, reading_str=reading_str),
        )
    return Section(version=versioninfo[0][0] if versioninfo else "", fans=fans)


def discover_netgear_fans(section: Section) -> DiscoveryResult:
    for sensorname, fan in section.fans.items():
        if fan.state != "1" and not (fan.state == "2" and fan.reading_str == "0"):
            yield Service(item=sensorname)


def check_netgear_fans(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    fan = section.fans.get(item)
    if fan is None:
        return

    if fan.reading_str != "Not Supported":
        yield from check_fan(int(fan.reading_str), params)
    state, state_readable = netgear_map_state_txt_to_state(fan.state, section.version)
    yield Result(state=state, summary=f"Status: {state_readable}")


snmp_section_netgear_fans = SNMPSection(
    name="netgear_fans",
    detect=DETECT_NETGEAR,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.4526.10.1.1.1",
            oids=["13"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.4526.10.43.1.6.1",
            oids=[OIDEnd(), "3", "4"],
        ),
    ],
    parse_function=parse_netgear_fans,
)


check_plugin_netgear_fans = CheckPlugin(
    name="netgear_fans",
    service_name="Fan %s",
    discovery_function=discover_netgear_fans,
    check_function=check_netgear_fans,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (1500, 1200),
    },
)

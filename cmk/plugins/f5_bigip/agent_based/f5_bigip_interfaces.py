#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    any_of,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    get_rate,
    get_value_store,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

# .1.3.6.1.4.1.3375.2.1.2.4.4.3.1.1.  index for ifname
# .1.3.6.1.4.1.3375.2.1.2.4.1.2.1.17. index for ifstate
# .1.3.6.1.4.1.3375.2.1.2.4.4.3.1.3.  index for IN bytes
# .1.3.6.1.4.1.3375.2.1.2.4.4.3.1.5.  index for OUT bytes

_UP = 0

_STATE_NAMES = {
    _UP: "Up",
    1: "Down (has no link and is initialized)",
    2: "Disabled (has been forced down)",
    3: "Uninitialized (has not been initialized)",
    4: "Loopback (in loopback mode)",
    5: "Unpopulated (interface not physically populated)",
}


@dataclass(frozen=True)
class Interface:
    state: int
    inbytes: int
    outbytes: int


Section = Mapping[str, Interface]


def parse_f5_bigip_interfaces(string_table: StringTable) -> Section:
    section = {}
    for port, ifstate, inbytes, outbytes in string_table:
        # The device leaves the columns of OIDs it does not answer empty; a port without
        # a state or without counters cannot be checked. Every other value has to be a
        # number, so a non-numeric one is left to crash.
        if not (ifstate and inbytes and outbytes):
            continue
        section[port] = Interface(state=int(ifstate), inbytes=int(inbytes), outbytes=int(outbytes))
    return section


def discover_f5_bigip_interfaces(section: Section) -> DiscoveryResult:
    yield from (Service(item=port) for port, interface in section.items() if interface.state == _UP)


def check_f5_bigip_interfaces(item: str, section: Section) -> CheckResult:
    if (interface := section.get(item)) is None:
        return

    if (state_name := _STATE_NAMES.get(interface.state)) is None:
        yield Result(state=State.UNKNOWN, summary=f"Unknown state ({interface.state})")
        return

    yield Result(
        state=State.OK if interface.state == _UP else State.CRIT,
        summary=state_name,
    )
    if interface.state != _UP:
        return

    value_store = get_value_store()
    this_time = int(time.time())
    for direction, counter in (("in", interface.inbytes), ("out", interface.outbytes)):
        yield from check_levels(
            get_rate(value_store, direction, this_time, counter),
            metric_name=f"bytes_{direction}",
            render_func=render.iobandwidth,
            label=f"{direction.capitalize()} bytes",
        )


snmp_section_f5_bigip_interfaces = SimpleSNMPSection(
    name="f5_bigip_interfaces",
    detect=any_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3375.2.1.3.4.10"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3375.2.1.3.4.20"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.1.2.4",
        oids=[
            "4.3.1.1",  # ifname
            "1.2.1.17",  # ifstate
            "4.3.1.3",  # IN bytes
            "4.3.1.5",  # OUT bytes
        ],
    ),
    parse_function=parse_f5_bigip_interfaces,
)


check_plugin_f5_bigip_interfaces = CheckPlugin(
    name="f5_bigip_interfaces",
    service_name="f5 Interface %s",
    discovery_function=discover_f5_bigip_interfaces,
    check_function=check_f5_bigip_interfaces,
)

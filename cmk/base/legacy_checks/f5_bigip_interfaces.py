#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import dataclasses
import time
from collections.abc import Iterable, Mapping

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import (
    any_of,
    equals,
    get_rate,
    get_value_store,
    render,
    SNMPTree,
    StringTable,
)

check_info = {}

# .1.3.6.1.4.1.3375.2.1.2.4.4.3.1.1.  index for ifname
# .1.3.6.1.4.1.3375.2.1.2.4.1.2.1.17. index for ifstate
# .1.3.6.1.4.1.3375.2.1.2.4.4.3.1.3.  index for IN bytes
# .1.3.6.1.4.1.3375.2.1.2.4.4.3.1.5.  index for OUT bytes


@dataclasses.dataclass
class Interface:
    state: int
    inbytes: int
    outbytes: int


Section = Mapping[str, Interface]


def parse_f5_bigip_interfaces(string_table: StringTable) -> Section:
    section = {}
    for port, ifstate, inbytes, outbytes in string_table:
        try:
            section[port] = Interface(
                state=int(ifstate), inbytes=int(inbytes), outbytes=int(outbytes)
            )
        except ValueError:
            pass
    return section


def discover_f5_bigip_interfaces(section: Section) -> Iterable[tuple[str, dict]]:
    yield from ((port, {}) for port, interface in section.items() if interface.state == 0)


def check_f5_bigip_interfaces(item, _no_params, section):
    if (interface := section.get(item)) is None:
        return

    match interface.state:
        case 0:
            yield 0, "Up"
        case 1:
            yield 2, "Down (has no link and is initialized)"
        case 2:
            yield 2, "Disabled (has been forced down)"
        case 3:
            yield 2, "Uninitialized (has not been initialized)"
        case 4:
            yield 2, "Loopback (in loopback mode)"
        case 5:
            yield 2, "Unpopulated (interface not physically populated)"
        case unknown_state:
            yield 3, f"Unknown state ({unknown_state})"

    if interface.state != 0:
        return

    this_time = int(time.time())
    value_store = get_value_store()
    yield check_levels(
        get_rate(value_store, "in", this_time, interface.inbytes),
        "bytes_in",
        None,
        human_readable_func=render.iobandwidth,
        infoname="In bytes",
    )

    yield check_levels(
        get_rate(value_store, "out", this_time, interface.outbytes),
        "bytes_out",
        None,
        human_readable_func=render.iobandwidth,
        infoname="Out bytes",
    )


check_info["f5_bigip_interfaces"] = LegacyCheckDefinition(
    name="f5_bigip_interfaces",
    detect=any_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3375.2.1.3.4.10"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3375.2.1.3.4.20"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.1.2.4",
        oids=["4.3.1.1", "1.2.1.17", "4.3.1.3", "4.3.1.5"],
    ),
    service_name="f5 Interface %s",
    parse_function=parse_f5_bigip_interfaces,
    discovery_function=discover_f5_bigip_interfaces,
    check_function=check_f5_bigip_interfaces,
)

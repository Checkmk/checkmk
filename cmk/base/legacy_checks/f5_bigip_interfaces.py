#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import dataclasses
import time
from collections.abc import Iterable, Mapping

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    any_of,
    equals,
    get_rate,
    get_value_store,
    render,
    SNMPTree,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

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


f5_bigip_interface_states = {
    1: "down (has no link and is initialized)",
    2: "disabled (has been forced down)",
    3: "uninitialized (has not been initialized)",
    4: "loopback (in loopback mode)",
    5: "unpopulated (interface not physically populated)",
}


def check_f5_bigip_interfaces(item, _no_params, section):
    if (interface := section.get(item)) is None:
        return

    if interface.state != 0:
        yield (
            2,
            "State of {} is {}".format(
                f5_bigip_interface_states.get(interface.state, "unhandled (%d)" % interface.state),
                interface.port,
            ),
        )
        return

    this_time = int(time.time())
    value_store = get_value_store()
    in_per_sec = get_rate(value_store, "in", this_time, interface.inbytes)
    out_per_sec = get_rate(value_store, "out", this_time, interface.outbytes)

    inbytes_h = render.iobandwidth(in_per_sec)
    outbytes_h = render.iobandwidth(out_per_sec)
    perf = [
        ("bytes_in", in_per_sec),
        ("bytes_out", out_per_sec),
    ]
    yield 0, f"in bytes: {inbytes_h}, out bytes: {outbytes_h}", perf


check_info["f5_bigip_interfaces"] = LegacyCheckDefinition(
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

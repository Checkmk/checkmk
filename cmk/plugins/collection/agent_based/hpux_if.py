#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import AgentSection, CheckPlugin, RuleSetType, StringTable
from cmk.plugins.lib import if64, interfaces

_HPUX_FIELDS_TO_IF_FIELDS = {
    "Inbound Octets": "in_octets",
    "Inbound Unicast Packets": "in_ucast",
    "Inbound Multicast Packets": "in_mcast",
    "Inbound Broadcast Packets": "in_bcast",
    "Inbound Discards": "in_disc",
    "Inbound Errors": "in_err",
    "Outbound Octets": "out_octets",
    "Outbound Unicast Packets": "out_ucast",
    "Outbound Multicast Packets": "out_mcast",
    "Outbound Broadcast Packets": "out_bcast",
    "Outbound Discards": "out_disc",
    "Outbound Errors": "out_err",
}


def parse_hpux_if(
    string_table: StringTable,
) -> interfaces.Section[interfaces.InterfaceWithCounters]:
    nics = []
    for line in string_table:
        if "***" in line:
            iface = interfaces.InterfaceWithCounters(
                interfaces.Attributes(
                    index="0",
                    descr="0",
                    alias="0",
                    type="6",
                ),
                interfaces.Counters(),
            )
            nics.append(iface)
            continue
        if "=" not in line:
            continue

        left, right = " ".join(line).split("=")
        left = left.strip()
        right = right.strip()

        if left == "PPA Number":
            iface.attributes.index = right
        elif left == "Interface Name":
            iface.attributes.descr = iface.attributes.alias = right
        elif left == "Speed":
            iface.attributes.speed = hpux_parse_speed(right)
        elif left == "Operation Status":
            iface.attributes.oper_status = hpux_parse_operstatus(right)
        elif left == "Station Address":
            h = right[2:]
            iface.attributes.phys_address = "".join(
                [chr(int(x + y, 16)) for (x, y) in zip(h[::2], h[1::2])]
            )
        elif left in _HPUX_FIELDS_TO_IF_FIELDS:
            setattr(
                iface.counters,
                _HPUX_FIELDS_TO_IF_FIELDS[left],
                interfaces.saveint(right),
            )

    for iface in nics:
        iface.attributes.finalize()

    return nics


def hpux_parse_speed(speed: str) -> float:
    parts = speed.split()
    if parts[1] == "Gbps":
        mult = 1000 * 1000 * 1000
    else:
        mult = 1000 * 1000
    return float(parts[0]) * mult


def hpux_parse_operstatus(txt: str) -> str:
    return "1" if txt.lower() == "up" else "2"


agent_section_hpux_if = AgentSection(
    name="hpux_if",
    parse_function=parse_hpux_if,
)

check_plugin_hpux_if = CheckPlugin(
    name="hpux_if",
    service_name="NIC %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=interfaces.discover_interfaces,
    check_ruleset_name="interfaces",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=if64.generic_check_if64,
    cluster_check_function=interfaces.cluster_check,
)

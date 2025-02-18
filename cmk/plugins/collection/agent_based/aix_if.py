#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.lib import interfaces


def _parse_aix_common(  # pylint: disable=too-many-branches
    string_table: StringTable,
) -> tuple[dict[str, interfaces.InterfaceWithCounters], dict[str, list[str]]]:
    ifaces = {}
    flags = {}
    index = 0
    for line in string_table:
        if line[0].startswith("["):
            nic = line[0][1:-1]
            index += 1
            ifaces[nic] = iface = interfaces.InterfaceWithCounters(
                interfaces.Attributes(
                    index=str(index),
                    descr=nic,
                    alias=nic,
                    type="24" if nic.startswith("lo") else "6",
                ),
                interfaces.Counters(),
            )
        elif line[0] == "Bytes:" and line[2] == "Bytes:":
            iface.counters.out_octets = interfaces.saveint(line[1])
            iface.counters.in_octets = interfaces.saveint(line[3])
        elif line[0] == "Packets:" and line[2] == "Packets:":
            iface.counters.out_ucast = interfaces.saveint(line[1])
            iface.counters.in_ucast = interfaces.saveint(line[3])
        elif line[0] == "Transmit" and line[1] == "Errors:":
            iface.counters.out_err = interfaces.saveint(line[2])
            iface.counters.in_err = interfaces.saveint(line[5])
        elif " ".join(line[0:2]) == "Broadcast Packets:":
            iface.counters.out_bcast = interfaces.saveint(line[2])
            iface.counters.in_bcast = interfaces.saveint(line[5])
        elif " ".join(line[0:2]) == "Multicast Packets:":
            iface.counters.out_mcast = interfaces.saveint(line[2])
            iface.counters.in_mcast = interfaces.saveint(line[5])
        elif " ".join(line[0:2]) == "Hardware Address:":
            iface.attributes.phys_address = interfaces.mac_address_from_hexstring(line[2])
        elif " ".join(line[0:3]) == "Adapter Data Rate:":
            # speed is in Mb/s
            iface.attributes.speed = int(line[3]) * 1000000
        elif " ".join(line[0:2]) == "Driver Flags:":
            flags[nic] = line[2:]
        elif " ".join(line[0:3]) == "KIM Driver Flags:":
            flags[nic] = line[3:]
        elif line and ":" not in line and nic in flags:
            flags[nic] += line

    return ifaces, flags


def parse_aix_if(
    string_table: StringTable,
) -> interfaces.Section[interfaces.InterfaceWithCounters]:
    ifaces, flags = _parse_aix_common(string_table)

    for nic, iface in ifaces.items():
        iface_flags = flags.get(nic, [])
        if "Up" in iface_flags:
            iface.attributes.oper_status = "1"
        elif "Down" in flags:
            iface.attributes.oper_status = "2"
        # No information from entstat. We consider interfaces up
        # if they have been used at least some time since the
        # system boot.
        elif iface.counters.in_octets:
            iface.attributes.oper_status = "1"
        iface.attributes.finalize()

    return list(ifaces.values())


agent_section_aix_if = AgentSection(
    name="aix_if",
    parse_function=parse_aix_if,
    parsed_section_name="interfaces",
)

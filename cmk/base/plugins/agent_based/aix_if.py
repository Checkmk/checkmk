#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register, type_defs
from .utils import interfaces


def parse_aix_if(  # pylint: disable=too-many-branches
    string_table: type_defs.StringTable,
) -> interfaces.Section:
    ifaces = {}
    flags = {}
    index = 0
    for line in string_table:
        if line[0].startswith("["):
            nic = line[0][1:-1]
            index += 1
            ifaces[nic] = iface = interfaces.Interface(
                index=str(index),
                descr=nic,
                alias=nic,
                type="24" if nic.startswith("lo") else "6",
            )
        elif line[0] == "Bytes:" and line[2] == "Bytes:":
            iface.out_octets = interfaces.saveint(line[1])
            iface.in_octets = interfaces.saveint(line[3])
        elif line[0] == "Packets:" and line[2] == "Packets:":
            iface.out_ucast = interfaces.saveint(line[1])
            iface.in_ucast = interfaces.saveint(line[3])
        elif line[0] == "Transmit" and line[1] == "Errors:":
            iface.out_errors = interfaces.saveint(line[2])
            iface.in_errors = interfaces.saveint(line[5])
        elif " ".join(line[0:2]) == "Broadcast Packets:":
            iface.out_bcast = interfaces.saveint(line[2])
            iface.in_bcast = interfaces.saveint(line[5])
        elif " ".join(line[0:2]) == "Multicast Packets:":
            iface.out_mcast = interfaces.saveint(line[2])
            iface.in_mcast = interfaces.saveint(line[5])
        elif " ".join(line[0:2]) == "Hardware Address:":
            iface.phys_address = interfaces.mac_address_from_hexstring(line[2])
        elif " ".join(line[0:3]) == "Adapter Data Rate:":
            # speed is in Mb/s
            iface.speed = int(line[3]) * 1000000
        elif " ".join(line[0:2]) == "Driver Flags:":
            flags[nic] = line[2:]
        elif " ".join(line[0:3]) == "KIM Driver Flags:":
            flags[nic] = line[3:]
        elif line and ":" not in line and nic in flags:
            flags[nic] += line

    for nic, iface in ifaces.items():
        iface_flags = flags.get(nic, [])
        if "Up" in iface_flags:
            iface.oper_status = "1"
        elif "Down" in flags:
            iface.oper_status = "2"
        # No information from entstat. We consider interfaces up
        # if they have been used at least some time since the
        # system boot.
        elif iface.in_octets > 0:
            iface.oper_status = "1"
        iface.finalize()

    return list(ifaces.values())


register.agent_section(
    name="aix_if",
    parse_function=parse_aix_if,
    parsed_section_name="interfaces",
)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# 1.3.6.1.4.1.9.9.68.1.2.2.1.1 --> vmVlanType: static(1), dynamic(2), multiVlan(3)
# 1.3.6.1.4.1.9.9.68.1.2.2.1.2 --> vmVlan: id of the vlan the port is asssigned to
#                                  if type = 1 or 2.
#                                  it's 0 if the port is not assigned to a vlan
# 1.3.6.1.4.1.9.9.68.1.2.2.1.4 --> vmVlans: the vlans the port is assigned to
#                                  if the type = 3

# "The VLAN(s) the port is assigned to when the
# port's vmVlanType is set to multiVlan.
# This object is not instantiated if not applicable.

# The port is always assigned to one or more VLANs
# and the object may not be set so that there are
# no vlans assigned.

# Each octet within the value of this object specifies a
# set of eight VLANs, with the first octet specifying
# VLAN id 1 through 8, the second octet specifying VLAN
# ids 9 through 16, etc.   Within each octet, the most
# significant bit represents the lowest numbered
# VLAN id, and the least significant bit represents the
# highest numbered VLAN id.  Thus, each VLAN of the
# port is represented by a single bit within the
# value of this object.  If that bit has a value of
# '1' then that VLAN is included in the set of
# VLANs; the VLAN is not included if its bit has a
# value of '0'."

from .agent_based_api.v1 import contains, OIDEnd, register, SNMPTree, TableRow

register.snmp_section(
    name="inv_cisco_vlans",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.68.1.2.2.1",
            oids=[
                OIDEnd(),
                "1",  # vmVlanType
                "2",  # vmVlan
                "4",  # vmVlans
            ],
        ),
    ],
    detect=contains(".1.3.6.1.2.1.1.1.0", "cisco"),
)


def parse_multi_vlan(vlan_multi):
    """compress a list of vlans into a readable format"""

    def concatenate_vlans(vlan, subinfo):
        if vlan not in subinfo:
            subinfo.append(vlan)
        return "-".join(map(str, subinfo))

    vlans = []
    for k, hex_ in enumerate(vlan_multi):
        for l, bit in enumerate(bin(ord(hex_))[2:]):
            if bit == "1":
                vlans.append(k * 8 + l + 1)

    if not vlans:
        return ""

    infotexts = []
    subinfo = vlans[:1]
    last_vlan = vlans[0]

    for vlan in vlans[1:]:
        if vlan - last_vlan > 1:
            infotexts.append(concatenate_vlans(last_vlan, subinfo))
            subinfo = [vlan]

        if vlan == vlans[-1]:
            infotexts.append(concatenate_vlans(vlan, subinfo))

        last_vlan = vlan

    return ", ".join(infotexts)


def inv_cisco_vlans(section):
    path = ["networking", "interfaces"]
    map_vlans = {
        "1": "static",
        "2": "dynamic",
        "3": "multi-VLAN",
    }

    for if_id, vlan_type, vlan_single, vlan_multi in section[0]:
        vlan_readable = map_vlans.get(vlan_type, "")
        vlans = None
        if vlan_single != "0" and vlan_type in ["1", "2"]:
            vlans = vlan_single
        elif vlan_type == "3":
            vlans = parse_multi_vlan(vlan_multi)

        if vlans:
            yield TableRow(
                path=path,
                key_columns={"index": int(if_id)},
                inventory_columns={
                    "vlans": vlans,
                    "vlantype": vlan_readable,
                },
            )


register.inventory_plugin(
    name="inv_cisco_vlans",
    inventory_function=inv_cisco_vlans,
)

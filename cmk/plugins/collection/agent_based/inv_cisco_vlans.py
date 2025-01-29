#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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

from collections.abc import Sequence
from typing import NamedTuple

from cmk.agent_based.v2 import (
    InventoryPlugin,
    InventoryResult,
    OIDEnd,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
    TableRow,
)
from cmk.plugins.lib.cisco import DETECT_CISCO


class _IfInfo(NamedTuple):
    id_: int
    vlans: str
    vlan_type: str


Section = Sequence[_IfInfo]
MAP_VLANS = {
    "1": "static",
    "2": "dynamic",
    "3": "multi-VLAN",
}


def _bitmask(raw: str) -> Sequence[int]:
    """
    >>> _bitmask("F")
    [1, 5, 6]

    >>> _bitmask("FF FF")
    [1, 5, 6, 9, 13, 14, 17, 25, 29, 30, 33, 37, 38]

    >>> _bitmask("80 40 00 00 01 00 F0 00")
    [1, 2, 3, 9, 10, 17, 25, 26, 28, 33, 34, 41, 49, 50, 57, 58, 65, 73, 74, 81, 82, 89, 97, 98, 105, 106, 110, 113, 121, 122, 129, 130, 137, 145, 149, 150, 153, 154, 161, 169, 170, 177, 178]

    """
    # This is the state as I refactor this.
    # I am not convinced this is right.
    #
    #  for k, hex_ in enumerate(raw.split())
    #  for index, flag in enumerate(bin(int(hex_, 16))[2:])
    #
    # Looks better to me -- but there are no tests.
    # The above would result in
    #
    #  >>> _bitmask("FF FF")
    #  [1, 2, 3, 4, ..., 15, 16]
    #
    return [
        k * 8 + index + 1
        for k, hex_ in enumerate(raw)
        for index, flag in enumerate(bin(ord(hex_))[2:])
        if flag == "1"
    ]


def _parse_multi_vlan(vlan_multi: str) -> str:
    """compress a list of vlans into a readable format

    I am not sure if this is correct:

    >>> _parse_multi_vlan("80 40 00 00 01 00 F0 00")
    '1-3, 9-10, 17, 25-26, 28, 33-34, 41, 49-50, 57-58, 65, 73-74, 81-82, 89, 97-98, 105-106, 110, 113, 121-122, 129-130, 137, 145, 149-150, 153-154, 161, 169-170, 177-178'
    >>> _parse_multi_vlan("FF FF")
    '1, 5-6, 9, 13-14, 17, 25, 29-30, 33, 37-38'
    """

    vlans = _bitmask(vlan_multi)

    if not vlans:
        return ""

    return _render_vlan_lists(vlans)


def _render_vlan_lists(vlans: Sequence[int]) -> str:
    """
    >>> _render_vlan_lists([1, 2, 3, 4, 6, 8, 9, 12])
    '1-4, 6, 8-9, 12'
    """
    succ_vals: list[set[int]] = []
    for i in sorted(set(vlans)):
        if succ_vals and i - 1 in succ_vals[-1]:
            succ_vals[-1].add(i)
        else:
            succ_vals.append({i})

    return ", ".join(str(s.pop()) if len(s) == 1 else f"{min(s)}-{max(s)}" for s in succ_vals)


def parse_inv_cisco_vlans(string_table: StringTable) -> Section:
    section = []
    for if_id, vlan_type, vlan_single, vlan_multi in string_table:
        vlan_readable = MAP_VLANS.get(vlan_type, "")
        if vlan_single != "0" and vlan_type in ["1", "2"]:
            section.append(_IfInfo(int(if_id), vlan_single, vlan_readable))
        elif vlan_type == "3":
            section.append(_IfInfo(int(if_id), _parse_multi_vlan(vlan_multi), vlan_readable))

    return section


snmp_section_inv_cisco_vlans = SimpleSNMPSection(
    name="inv_cisco_vlans",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.68.1.2.2.1",
        oids=[
            OIDEnd(),
            "1",  # vmVlanType
            "2",  # vmVlan
            "4",  # vmVlans
        ],
    ),
    detect=DETECT_CISCO,
    parse_function=parse_inv_cisco_vlans,
)


def inv_cisco_vlans(section: Section) -> InventoryResult:
    yield from (
        TableRow(
            path=["networking", "interfaces"],
            key_columns={"index": if_info.id_},
            inventory_columns={
                "vlans": if_info.vlans,
                "vlantype": if_info.vlan_type,
            },
        )
        for if_info in section
    )


inventory_plugin_inv_cisco_vlans = InventoryPlugin(
    name="inv_cisco_vlans",
    inventory_function=inv_cisco_vlans,
)

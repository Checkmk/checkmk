#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, List, Mapping, Union

from .agent_based_api.v1 import all_of, any_of, contains, OIDEnd, register, SNMPTree
from .agent_based_api.v1.type_defs import StringByteTable
from .utils import if64, interfaces

StringByteLine = List[Union[str, List[int]]]

IF64_BASE_TREE = SNMPTree(
    base=if64.BASE_OID,
    oids=if64.END_OIDS[:1]
    + [
        "31.1.1.1.1",  #  1 ifName (brocade and lancom have no useful information in ifDescr)
    ]
    + if64.END_OIDS[2:3]
    + [
        "31.1.1.1.15",  # 3 ifHighSpeed, 1000 means 1Gbit
    ]
    + if64.END_OIDS[4:-1]
    + [
        "2.2.1.2",  #    -1 ifDescr, used in order to ignore some logical NICs
    ],
)


def _map_ports(ethernet_ports_assignment: StringByteTable) -> Mapping[str, str]:
    """Create physical to virtual ports map

    Lancom defines a mapping from physical to virtual ports
    at LCOS-MIB::lcsStatusEthernetPortsPortsEntry (.1.3.6.1.4.1.2356.11.1.51.1.1)
    >>> _map_ports([
    ...     ['2', '0'],
    ...     ['3', '512'],
    ...     ['4', '2'],
    ...     ['5', '3'],
    ...     ['17', '4'],
    ...     ['18', '5'],
    ... ])
    {'ETH-1': 'LAN-1', 'ETH-2': 'DSL-1', 'ETH-3': 'LAN-3', 'ETH-4': 'LAN-4', 'WAN-1': 'LAN-5', 'WAN-2': 'LAN-6'}
    """
    # lcsStatusEthernetPortsPortsEntryPort
    physical_port = {
        "1": "uplink",
        "2": "ETH-1",
        "3": "ETH-2",
        "4": "ETH-3",
        "5": "ETH-4",
        "16": "WAN",
        "17": "WAN-1",
        "18": "WAN-2",
        "32": "SFP-1",
    }
    # lcsStatusEthernetPortsPortsEntryAssignment
    virtual_port = {
        "0": "LAN-1",
        "1": "LAN-2",
        "2": "LAN-3",
        "3": "LAN-4",
        "4": "LAN-5",
        "5": "LAN-6",
        "512": "DSL-1",
        "513": "DSL-2",
        "514": "DSL-3",
        "515": "DSL-4",
        "516": "DSL-5",
    }
    return {
        physical_port.get(str(e[0]), "unknown"): virtual_port.get(str(e[1]), "unknown")
        for e in ethernet_ports_assignment
    }


def _augment_name(
    line: StringByteLine,
    description: str,
    name_map: Mapping[str, str],
) -> StringByteLine:
    """This function changes contents of @line which each only apply to Lancom or Brocade
    routers. Since we have to split off @description anyway we apply both changes in
    one place rather than in dedicated locations.
    """
    index, name_raw, type_str, speed, *rest = line
    name = str(name_raw)
    return [
        index,
        (  # augment name - applies to Lancom routers only
            f"{name} Logical {name_map.get(name, '')}"  #
            if description.startswith("Logical Network")
            else name
        ).strip(),
        type_str,
        if64.fix_if_64_highspeed(str(speed)),  # apllies to Brocade routers only
        *rest,
    ]


def parse_if_brocade_lancom(
    if_table: StringByteTable,
    name_map: Mapping[str, str],
    port_map: Mapping[str, str],
    ignore_descriptions: Iterable[str],
) -> interfaces.Section:
    """
    >>> for result in parse_if_brocade_lancom([
    ...       ['1', 'eth0', '2', '30', '1', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    ...        '10', '11', '12', '13', 'eth0', [0, 12, 206, 149, 55, 128], 'Local0'],
    ...       ['1', 'eth0', '2', '30', '1', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    ...        '10', '11', '12', '13', 'eth1', [0, 12, 206, 149, 55, 128], 'Logical Network'],
    ...     ],
    ...     {'eth0': 'LAN'},
    ...     {},
    ...     {'Local'}):
    ...   print(result.descr, result.alias, result.speed)
    eth0 Logical LAN eth1 30000000
    """
    return if64.generic_parse_if64(
        [
            _augment_name(line, description, name_map)
            for *line, description in if_table
            if isinstance(description, str)
            if not any(description.startswith(d) for d in ignore_descriptions)
        ],
        port_map,
    )


def parse_if_brocade(string_table: StringByteTable) -> interfaces.Section:
    return parse_if_brocade_lancom(
        if_table=string_table,
        name_map={},
        port_map={},
        ignore_descriptions={"Point-2-Point"},
    )


def parse_if_lancom(string_table: List[StringByteTable]) -> interfaces.Section:
    if_table, ssid_table, port_mapping = string_table
    return parse_if_brocade_lancom(
        if_table,
        name_map={str(ssid_line[0]): str(ssid_line[1]) for ssid_line in ssid_table},
        port_map=_map_ports(port_mapping),
        ignore_descriptions={"P2P", "Point-2-Point"},
    )


register.snmp_section(
    name="if_brocade",
    parse_function=parse_if_brocade,
    parsed_section_name="interfaces",
    fetch=IF64_BASE_TREE,
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "Brocade VDX Switch"),
        if64.HAS_ifHCInOctets,
    ),
    supersedes=["if", "if64"],
)

register.snmp_section(
    name="if_lancom",
    parse_function=parse_if_lancom,
    parsed_section_name="interfaces",
    fetch=[
        IF64_BASE_TREE,
        # Lancom LCOS-MIB::lcsStatusWlanNetworksEntry
        SNMPTree(
            base=".1.3.6.1.4.1.2356.11.1.3.56.1",
            oids=[
                "1",  # lcsStatusWlanNetworksEntryIfc
                "3",  # lcsStatusWlanNetworksEntryNetworkName
            ],
        ),
        # Lancom LCOS-MIB::lcsStatusEthernetPortsPortsEntry
        SNMPTree(
            base=".1.3.6.1.4.1.2356.11.1.51.1.1",
            oids=[
                OIDEnd(),
                "7",  # lcsStatusEthernetPortsPortsEntryAssignment
            ],
        ),
    ],
    detect=any_of(
        any_of(
            *(contains(".1.3.6.1.2.1.1.1.0", name) for name in ("LANCOM", "ELSA", "T-Systems")),
        ),
        all_of(
            contains(".1.3.6.1.2.1.1.1.0", "LAN R800V"),
            if64.HAS_ifHCInOctets,
        ),
    ),
    supersedes=["if", "if64"],
)

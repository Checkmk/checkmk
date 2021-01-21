#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, List, Union, Mapping

from .agent_based_api.v1.type_defs import StringByteTable
from .agent_based_api.v1 import (
    all_of,
    any_of,
    contains,
    register,
    SNMPTree,
)
from .utils import if64, interfaces

StringByteLine = List[Union[str, List[int]]]

IF64_BASE_TREE = SNMPTree(
    base=if64.BASE_OID,
    oids=if64.END_OIDS[:1] + [
        "31.1.1.1.1",  #  1 ifName (brocade and lancom have no useful information in ifDescr)
    ] + if64.END_OIDS[2:3] + [
        "31.1.1.1.15",  # 3 ifHighSpeed, 1000 means 1Gbit
    ] + if64.END_OIDS[4:-1] + [
        "2.2.1.2",  #    -1 ifDescr, used in order to ignore some logical NICs
    ],
)


def _fix_line(
    line: StringByteLine,
    description: str,
    name_map: Mapping[str, str],
) -> StringByteLine:
    """This function changes contents of @line which each only apply to Lancom or Brocade
    routers. Since we have to split off @description anyway we apply both changes in
    one place rather than in dedicated locations."""
    index, name_raw, type_str, speed, *rest = line
    name = str(name_raw)
    return [
        index,
        (  # augment name - applies to Lancom routers only
            f"{name} Logical {name_map.get(name, '')}"  #
            if description.startswith("Logical Network") else name).strip(),
        type_str,
        if64.fix_if_64_highspeed(str(speed)),  # apllies to Brocade routers only
        *rest,
    ]


def parse_if_brocade_lancom(
    if_table: StringByteTable,
    name_map: Mapping[str, str],
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
    ...     {'Local'}):
    ...   print(result.descr, result.alias, result.speed)
    eth0 Logical LAN eth1 30000000
    """
    return if64.generic_parse_if64([[
        _fix_line(line, description, name_map)
        for *line, description in if_table
        if isinstance(description, str)
        if not any(description.startswith(d) for d in ignore_descriptions)
    ]])


def parse_if_brocade(string_table: StringByteTable) -> interfaces.Section:
    return parse_if_brocade_lancom(
        if_table=string_table,
        name_map={},
        ignore_descriptions={"Point-2-Point"},
    )


def parse_if_lancom(string_table: List[StringByteTable]) -> interfaces.Section:
    if_table, ssid_table = string_table
    return parse_if_brocade_lancom(
        if_table,
        name_map={str(ssid_line[0]): str(ssid_line[1]) for ssid_line in ssid_table},
        ignore_descriptions={"P2P", "Point-2-Point"},
    )


register.snmp_section(
    name="if_brocade",
    parse_function=parse_if_brocade,
    fetch=IF64_BASE_TREE,
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "Brocade VDX Switch"),
        if64.HAS_ifHCInOctets,
    ),
    supersedes=['if', 'if64'],
)

register.snmp_section(
    name="if_lancom",
    parse_function=parse_if_lancom,
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
    ],
    detect=any_of(
        any_of(
            *(contains(".1.3.6.1.2.1.1.1.0", name) for name in ("LANCOM", "ELSA", "T-Systems")),),
        all_of(
            contains(".1.3.6.1.2.1.1.1.0", "LAN R800V"),
            if64.HAS_ifHCInOctets,
        ),
    ),
    supersedes=['if', 'if64'],
)

register.check_plugin(
    name="if_brocade",
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=interfaces.discover_interfaces,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=if64.generic_check_if64,
    cluster_check_function=interfaces.cluster_check,
)

register.check_plugin(
    name="if_lancom",
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=interfaces.discover_interfaces,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=if64.generic_check_if64,
    cluster_check_function=interfaces.cluster_check,
)

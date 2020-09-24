#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable
from .agent_based_api.v1 import (
    all_of,
    any_of,
    contains,
    register,
    SNMPTree,
    type_defs,
)
from .utils import if64, interfaces

SNMP_TREES = [
    SNMPTree(
        base=if64.BASE_OID,
        oids=if64.END_OIDS[:1] + [
            "31.1.1.1.1",  # 1 ifName (brocade and lancom have no useful information in ifDescr)
        ] + if64.END_OIDS[2:3] + [
            "31.1.1.1.15",  # 3 ifHighSpeed, 1000 means 1Gbit
        ] + if64.END_OIDS[4:-1] + [
            "2.2.1.2",  # -1 ifDescr, used in order to ignore some logical NICs
        ],
    ),
    SNMPTree(
        base=".1.3.6.1.4.1.2356.11.1.3.56.1",
        oids=[
            "1",
            "3",
        ],
    ),
]


def parse_if_brocade_lancom(
    string_table: type_defs.SNMPStringByteTable,
    descriptions_to_ignore: Iterable[str],
) -> interfaces.Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_if_brocade_lancom([
    ... [['1', 'eth0', '2', '30', '1', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11',
    ...   '12', '13', 'eth0', [0, 12, 206, 149, 55, 128], 'description']],
    ... [['a', 'b']]],
    ... []))
    [Interface(index='1', descr='eth0', alias='eth0', type='2', speed=30000000, oper_status='1', in_octets=1, in_ucast=2, in_mcast=3, in_bcast=4, in_discards=5, in_errors=6, out_octets=7, out_ucast=8, out_mcast=9, out_bcast=10, out_discards=11, out_errors=12, out_qlen=13, phys_address=[0, 12, 206, 149, 55, 128], oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None)]
    >>> pprint(parse_if_brocade_lancom([
    ... [['1', 'eth0', '2', '30', '1', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11',
    ...   '12', '13', 'eth0', [0, 12, 206, 149, 55, 128], 'description']],
    ... [['a', 'b']]],
    ... ['descr']))
    []
    >>> pprint(parse_if_brocade_lancom([
    ... [['1', 'eth0', '2', '30', '1', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11',
    ...   '12', '13', 'eth0', [0, 12, 206, 149, 55, 128], 'Logical Network'],
    ...  ['2', 'eth1', '2', '30', '1', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11',
    ...   '12', '13', 'eth1', [0, 12, 206, 149, 55, 128], 'Logical Network']],
    ... [['eth0', 'migration-fun']]],
    ... ['descr']))
    [Interface(index='1', descr='eth0 Logical migration-fun', alias='eth0', type='2', speed=30000000, oper_status='1', in_octets=1, in_ucast=2, in_mcast=3, in_bcast=4, in_discards=5, in_errors=6, out_octets=7, out_ucast=8, out_mcast=9, out_bcast=10, out_discards=11, out_errors=12, out_qlen=13, phys_address=[0, 12, 206, 149, 55, 128], oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None),
     Interface(index='2', descr='eth1 Logical', alias='eth1', type='2', speed=30000000, oper_status='1', in_octets=1, in_ucast=2, in_mcast=3, in_bcast=4, in_discards=5, in_errors=6, out_octets=7, out_ucast=8, out_mcast=9, out_bcast=10, out_discards=11, out_errors=12, out_qlen=13, phys_address=[0, 12, 206, 149, 55, 128], oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None)]
    """

    if_table, ssid_table = string_table
    ssid_dict = {str(ssid_line[0]): str(ssid_line[1]) for ssid_line in ssid_table}
    new_info = []

    for line in if_table:
        description = str(line[-1])
        if any(
                description.startswith(descr_to_ignore)
                for descr_to_ignore in descriptions_to_ignore):
            continue

        name = str(line[1])
        if description.startswith("Logical Network"):
            ssid = ssid_dict.get(name)
            name += " Logical" + (" " + ssid if ssid else "")

        line[1] = name.strip()
        line[3] = if64.fix_if_64_highspeed(str(line[3]))
        new_info.append(line[:-1])

    return if64.generic_parse_if64([new_info])


def parse_if_brocade(string_table: type_defs.SNMPStringByteTable) -> interfaces.Section:
    return parse_if_brocade_lancom(
        string_table,
        ["Point-2-Point"],
    )


def parse_if_lancom(string_table: type_defs.SNMPStringByteTable) -> interfaces.Section:
    return parse_if_brocade_lancom(
        string_table,
        ["P2P", "Point-2-Point"],
    )


register.snmp_section(
    name="if_brocade",
    parse_function=parse_if_brocade,
    trees=SNMP_TREES,
    detect=all_of(contains(".1.3.6.1.2.1.1.1.0", "Brocade VDX Switch"), if64.HAS_ifHCInOctets),
    supersedes=['if', 'if64'],
)

register.snmp_section(
    name="if_lancom",
    parse_function=parse_if_lancom,
    trees=SNMP_TREES,
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
    discovery_ruleset_type="all",
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
    discovery_ruleset_type="all",
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=interfaces.discover_interfaces,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=if64.generic_check_if64,
    cluster_check_function=interfaces.cluster_check,
)

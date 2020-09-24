#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import (
    register,
    type_defs,
)
from .utils import if64, interfaces

_HPUX_FIELDS_TO_IF_FIELDS = {
    "Inbound Octets": "in_octets",
    "Inbound Unicast Packets": "in_ucast",
    "Inbound Multicast Packets": "in_mcast",
    "Inbound Broadcast Packets": "in_bcast",
    "Inbound Discards": "in_discards",
    "Inbound Errors": "in_errors",
    "Outbound Octets": "out_octets",
    "Outbound Unicast Packets": "out_ucast",
    "Outbound Multicast Packets": "out_mcast",
    "Outbound Broadcast Packets": "out_bcast",
    "Outbound Discards": "out_discards",
    "Outbound Errors": "out_errors",
}


def parse_hpux_if(string_table: type_defs.AgentStringTable) -> interfaces.Section:
    r"""
    >>> from pprint import pprint
    >>> pprint(parse_hpux_if([
    ... ['***', 'lan2', '64', 'bit', 'MIB', 'statistics:'],
    ... ['Interface', 'Name', '=', 'lan2'],
    ... ['PPA', 'Number', '=', '2'],
    ... ['Description', '=', 'lan2', 'HP', 'PCI-X', '1000Mbps', 'Release', 'B.11.31.1103'],
    ... ['Interface', 'Type', '=', '1000Base-SX'],
    ... ['MTU', 'Size', '=', '1500'],
    ... ['Speed', '=', '1', 'Gbps'],
    ... ['Station', 'Address', '=', '0x001A4BAC31B2'],
    ... ['Administration', 'Status', '=', 'UP'],
    ... ['Operation', 'Status', '=', 'UP'],
    ... ['Last', 'Change', '=', 'Mon', 'Jan', '30', '08:39:36', '2012'],
    ... ['Inbound', 'Octets', '=', '46729081959'],
    ... ['Inbound', 'Unicast', 'Packets', '=', '0'],
    ... ['Inbound', 'Multicast', 'Packets', '=', '0'],
    ... ['Inbound', 'Broadcast', 'Packets', '=', '452745382'],
    ... ['Inbound', 'Discards', '=', '117536051'],
    ... ['Inbound', 'Errors', '=', '0'],
    ... ['Inbound', 'Unknown', 'Protocols', '=', '337286760'],
    ... ['Outbound', 'Octets', '=', '0'],
    ... ['Outbound', 'Unicast', 'Packets', '=', '0'],
    ... ['Outbound', 'Multicast', 'Packets', '=', '0'],
    ... ['Outbound', 'Broadcast', 'Packets', '=', '0'],
    ... ['Outbound', 'Discards', '=', '0'],
    ... ['Outbound', 'Errors', '=', '0'],
    ... ['Counter', 'Discontinuity', 'Time', '=', 'Mon', 'Jan', '30', '08:39:34', '2012'],
    ... ['Physical', 'Promiscuous', 'Mode', '=', 'FALSE'],
    ... ['Physical', 'Connector', 'Present', '=', 'TRUE'],
    ... ['Interface', 'Alias', '='],
    ... ['Link', 'Up/Down', 'Trap', 'Enable', '=', 'Enabled'],
    ... ]))
    [Interface(index='2', descr='lan2', alias='lan2', type='6', speed=1000000000.0, oper_status='1', in_octets=46729081959, in_ucast=0, in_mcast=0, in_bcast=452745382, in_discards=117536051, in_errors=0, out_octets=0, out_ucast=0, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='\x00\x1aK¬1²', oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None)]
    """
    nics = []
    for line in string_table:

        if '***' in line:
            iface = interfaces.Interface(
                index='0',
                descr='0',
                alias='0',
                type='6',
            )
            nics.append(iface)
            continue
        if '=' not in line:
            continue

        left, right = " ".join(line).split("=")
        left = left.strip()
        right = right.strip()

        if left == "PPA Number":
            iface.index = right
        elif left == "Interface Name":
            iface.descr = iface.alias = right
        elif left == "Speed":
            iface.speed = hpux_parse_speed(right)
        elif left == "Operation Status":
            iface.oper_status = hpux_parse_operstatus(right)
        elif left == "Station Address":
            h = right[2:]
            iface.phys_address = "".join([chr(int(x + y, 16)) for (x, y) in zip(h[::2], h[1::2])])
        elif left in _HPUX_FIELDS_TO_IF_FIELDS:
            setattr(
                iface,
                _HPUX_FIELDS_TO_IF_FIELDS[left],
                interfaces.saveint(right),
            )

    for iface in nics:
        iface.finalize()

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


register.agent_section(
    name='hpux_if',
    parse_function=parse_hpux_if,
)

register.check_plugin(
    name="hpux_if",
    service_name="NIC %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type="all",
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=interfaces.discover_interfaces,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=if64.generic_check_if64,
    cluster_check_function=interfaces.cluster_check,
)

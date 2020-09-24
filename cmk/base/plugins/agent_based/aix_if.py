#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import (
    register,
    type_defs,
)
from .utils import interfaces, if64


def parse_aix_if(string_table: type_defs.AgentStringTable) -> interfaces.Section:
    r"""
    >>> from pprint import pprint
    >>> pprint(parse_aix_if([
    ... ['[en0]'], ['Hardware', 'Address:', '00:00:00:00:00:00'],
    ... ['Packets:', '201485224', 'Packets:', '252330366'],
    ... ['Bytes:', '366285856218', 'Bytes:', '116117685059'],
    ... ['General', 'Statistics:'],
    ... ['-------------------'],
    ... ['No', 'mbuf', 'Errors:', '0'],
    ... ['Adapter', 'Reset', 'Count:', '0'],
    ... ['Adapter', 'Data', 'Rate:', '20000'],
    ... ['Driver', 'Flags:', 'Up', 'Broadcast', 'Debug'],
    ... ['Running', 'Simplex', '64BitSupport'],
    ... ['ChecksumOffload', 'DataRateSet'],
    ... ['[en1]'],
    ... ['Hardware', 'Address:', '01:02:03:04:05:06'],
    ... ['Packets:', '451364492', 'Packets:', '606173007'],
    ... ['Bytes:', '8701785086915', 'Bytes:', '70611010508'],
    ... ['General', 'Statistics:'],
    ... ['-------------------'],
    ... ['No', 'mbuf', 'Errors:', '0'],
    ... ['Adapter', 'Reset', 'Count:', '0'],
    ... ['Adapter', 'Data', 'Rate:', '20000'],
    ... ['Driver', 'Flags:', 'Up', 'Broadcast', 'Running'],
    ... ['Simplex', '64BitSupport', 'ChecksumOffload'],
    ... ['DataRateSet']]))
    [Interface(index='1', descr='en0', alias='en0', type='6', speed=20000000000, oper_status='1', in_octets=116117685059, in_ucast=252330366, in_mcast=0, in_bcast=0, in_discards=0, in_errors=0, out_octets=366285856218, out_ucast=201485224, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='\x00\x00\x00\x00\x00\x00', oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None),
     Interface(index='2', descr='en1', alias='en1', type='6', speed=20000000000, oper_status='1', in_octets=70611010508, in_ucast=606173007, in_mcast=0, in_bcast=0, in_discards=0, in_errors=0, out_octets=8701785086915, out_ucast=451364492, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='\x01\x02\x03\x04\x05\x06', oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None)]
    """
    ifaces = {}
    flags = {}
    index = 0
    for line in string_table:
        if line[0].startswith('['):
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
)

register.check_plugin(
    name="aix_if",
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

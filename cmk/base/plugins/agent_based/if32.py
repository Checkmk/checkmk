#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import (
    exists,
    OIDBytes,
    register,
    SNMPTree,
    type_defs,
)
from .utils import if64, interfaces


def parse_if(string_table: type_defs.SNMPStringByteTable) -> interfaces.Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_if([[
    ... ['1', '1', '6', '100000000', '1', '539345078', '3530301', '494413', '0', '15', '231288017',
    ...  '3477770', '38668315', '0', '0', '0', [0, 38, 241, 198, 3, 255]]]]))
    [Interface(index='1', descr='1', alias='1', type='6', speed=100000000, oper_status='1', in_octets=539345078, in_ucast=3530301, in_mcast=494413, in_bcast=0, in_discards=0, in_errors=15, out_octets=231288017, out_ucast=3477770, out_mcast=0, out_bcast=38668315, out_discards=0, out_errors=0, out_qlen=0, phys_address=[0, 38, 241, 198, 3, 255], oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None)]
    """
    return [
        interfaces.Interface(
            index=str(line[0]),
            descr=str(line[1]),
            type=str(line[2]),
            speed=interfaces.saveint(line[3]),
            oper_status=str(line[4]),
            in_octets=interfaces.saveint(line[5]),
            in_ucast=interfaces.saveint(line[6]),
            in_mcast=interfaces.saveint(line[7]),
            in_bcast=0,
            in_discards=interfaces.saveint(line[8]),
            in_errors=interfaces.saveint(line[9]),
            out_octets=interfaces.saveint(line[10]),
            out_ucast=interfaces.saveint(line[11]),
            out_mcast=0,
            out_bcast=interfaces.saveint(line[12]),
            out_discards=interfaces.saveint(line[13]),
            out_errors=interfaces.saveint(line[14]),
            out_qlen=interfaces.saveint(line[15]),
            alias=str(line[1]),
            phys_address=line[16],
        ) for line in string_table[0] if interfaces.saveint(line[0]) > 0
    ]


register.snmp_section(
    name="if",
    parse_function=parse_if,
    trees=[
        SNMPTree(
            base=".1.3.6.1.2.1.2.2.1",
            oids=[
                "1",  # ifIndex                  0
                "2",  # ifDescr                  1
                "3",  # ifType                   2
                "5",  # ifSpeed                  3
                "8",  # ifOperStatus             4
                "10",  # ifInOctets              5
                "11",  # ifInUcastPkts           6
                "12",  # ifInNUcastPkts          7
                "13",  # ifInDiscards            8
                "14",  # ifInErrors              9
                "16",  # ifOutOctets             10
                "17",  # ifOutUcastPkts          11
                "18",  # ifOutNUcastPkts         12
                "19",  # ifOutDiscards           13
                "20",  # ifOutErrors             14
                "21",  # ifOutQLen               15
                OIDBytes("6"),  # ifPhysAddress  16
            ],
        ),
    ],
    detect=exists(".1.3.6.1.2.1.2.2.1.*"),
)

register.check_plugin(
    name="if",
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

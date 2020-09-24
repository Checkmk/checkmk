#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import (
    register,
    SNMPTree,
    type_defs,
)
from .utils import (
    hitachi_hnas,
    if64,
    interfaces,
)


def parse_hitachi_hnas_fc_if(string_table: type_defs.SNMPStringTable) -> interfaces.Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_hitachi_hnas_fc_if([[
    ... ['1', '0', '1', '4', '308224', '2162688', '0', '20', '1', '0', '0', '0', '0', '0'],
    ... ['1', '1', '3', '4', '0', '0', '2', '0', '0', '0', '0', '0', '0', '0'],
    ... ['2', '0', '1', '4', '34233856', '2300928', '0', '22', '1', '0', '0', '0', '0', '0'],
    ... ['2', '1', '3', '4', '0', '0', '2', '0', '0', '0', '0', '0', '0', '0'],
    ... ]]))
    [Interface(index='1000', descr='1.0', alias='1.0', type='', speed=4000000000, oper_status='1', in_octets=308224, in_ucast=0, in_mcast=0, in_bcast=0, in_discards=0, in_errors=21, out_octets=2162688, out_ucast=0, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='', oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None),
     Interface(index='1001', descr='1.1', alias='1.1', type='', speed=4000000000, oper_status='2', in_octets=0, in_ucast=0, in_mcast=0, in_bcast=0, in_discards=0, in_errors=2, out_octets=0, out_ucast=0, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='', oper_status_name='down', speed_as_text='', group=None, node=None, admin_status=None),
     Interface(index='2000', descr='2.0', alias='2.0', type='', speed=4000000000, oper_status='1', in_octets=34233856, in_ucast=0, in_mcast=0, in_bcast=0, in_discards=0, in_errors=23, out_octets=2300928, out_ucast=0, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='', oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None),
     Interface(index='2001', descr='2.1', alias='2.1', type='', speed=4000000000, oper_status='2', in_octets=0, in_ucast=0, in_mcast=0, in_bcast=0, in_discards=0, in_errors=2, out_octets=0, out_ucast=0, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='', oper_status_name='down', speed_as_text='', group=None, node=None, admin_status=None)]
    """
    return [
        interfaces.Interface(
            index="%d%03d" % (int(line[0]), int(line[1])),
            descr=line[0] + "." + line[1],  # ClusterNode.InterfaceIndex
            alias=line[0] + "." + line[1],  # same as description
            type="",
            speed=int(line[3]) * 1000000000,
            oper_status=line[2] == "1" and "1" or "2",
            in_octets=interfaces.saveint(line[4]),
            in_discards=interfaces.saveint(line[13]),
            in_errors=sum(map(int, line[6:13])),
            out_octets=interfaces.saveint(line[5]),
        ) for line in string_table[0]
    ]


register.snmp_section(
    name="hitachi_hnas_fc_if",
    parse_function=parse_hitachi_hnas_fc_if,
    trees=[
        SNMPTree(
            base=".1.3.6.1.4.1.11096.6.1.1.1.3.6.25.1",
            oids=[
                "1",  # fcStatsClusterNode           0
                "2",  # fcStatsInterfaceIndex        1
                "4",  # fcStatsInterfaceStatus       2
                "5",  # fcStatsInterfaceLinkSpeed    3
                "7",  # fcStatsInstantaneousInRate   4
                "8",  # fcStatsInstantaneousOutRate  5
                "13",  # fcStatsSignalLossErrors      6
                "14",  # fcStatsBadRXCharErrors       7
                "15",  # fcStatsLossSyncErrors        8
                "16",  # fcStatsLinkFailErrors        9
                "17",  # fcStatsRXEOFErrors          10
                "19",  # fcStatsBadCRCErrors         11
                "20",  # fcStatsProtocolErrors       12
                "18",  # fcStatsDiscardedFrameErrors 13
            ],
        ),
    ],
    detect=hitachi_hnas.DETECT,
)

register.check_plugin(
    name="hitachi_hnas_fc_if",
    service_name="Interface FC %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type="all",
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=interfaces.discover_interfaces,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=if64.generic_check_if64,
    cluster_check_function=interfaces.cluster_check,
)

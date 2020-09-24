#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import (
    all_of,
    contains,
    OIDBytes,
    register,
    SNMPTree,
    type_defs,
)
from .utils import if64, interfaces


def parse_if64_tplink(string_table: type_defs.SNMPStringByteTable) -> interfaces.Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_if64_tplink([[
    ... ['1', 'Vlan-interface1', '6', '0', '1', '377138653', '0', '322566', '0', '0', '0',
    ...  '833158925', '0', '0', '0', '0', '0', '0', '', [172, 132, 198, 175, 52, 255], ''],
    ... ['49153', 'gigabitEthernet 1/0/1 : copper', '6', '1000', '1', '304751823764', '273677445',
    ...  '622053', '471593', '0', '0', '28059984507', '146316671', '2292666', '221224', '0', '0',
    ...  '0', '', [172, 132, 198, 175, 52, 255], 'ifAlias']
    ... ]]))
    [Interface(index='1', descr='Vlan-interface1', alias='', type='6', speed=0, oper_status='1', in_octets=377138653, in_ucast=0, in_mcast=322566, in_bcast=0, in_discards=0, in_errors=0, out_octets=833158925, out_ucast=0, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address=[172, 132, 198, 175, 52, 255], oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None),
     Interface(index='49153', descr='gigabitEthernet 1/0/1 : copper', alias='ifAlias', type='6', speed=1000000000, oper_status='1', in_octets=304751823764, in_ucast=273677445, in_mcast=622053, in_bcast=471593, in_discards=0, in_errors=0, out_octets=28059984507, out_ucast=146316671, out_mcast=2292666, out_bcast=221224, out_discards=0, out_errors=0, out_qlen=0, phys_address=[172, 132, 198, 175, 52, 255], oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None)]
    """
    preprocessed_lines = []
    for line in string_table[0]:
        # if we have no special alias info we use the standard ifAlias info
        if not line[18]:
            line[18] = line[20]
        line[3] = if64.fix_if_64_highspeed(str(line[3]))
        # cut away the last column with the optional ifAlias info
        preprocessed_lines.append(line[:20])
    return if64.generic_parse_if64([preprocessed_lines])


register.snmp_section(
    name="if64_tplink",
    parse_function=parse_if64_tplink,
    trees=[
        SNMPTree(
            base=".1.3.6.1",
            oids=[
                "2.1.2.2.1.1",  # ifIndex                    0
                "2.1.2.2.1.2",  # ifDescr                    1
                "2.1.2.2.1.3",  # ifType                     2
                "2.1.31.1.1.1.15",  # ifHighSpeed            .. 1000 means 1Gbit
                "2.1.2.2.1.8",  # ifOperStatus               4
                "2.1.31.1.1.1.6",  # ifHCInOctets            5
                "2.1.31.1.1.1.7",  # ifHCInUcastPkts         6
                "2.1.31.1.1.1.8",  # ifHCInMulticastPkts     7
                "2.1.31.1.1.1.9",  # ifHCInBroadcastPkts     8
                "2.1.2.2.1.13",  # ifInDiscards              9
                "2.1.2.2.1.14",  # ifInErrors               10
                "2.1.31.1.1.1.10",  # ifHCOutOctets         11
                "2.1.31.1.1.1.11",  # ifHCOutUcastPkts      12
                "2.1.31.1.1.1.12",  # ifHCOutMulticastPkts  13
                "2.1.31.1.1.1.13",  # ifHCOutBroadcastPkts  14
                "2.1.2.2.1.19",  # ifOutDiscards            15
                "2.1.2.2.1.20",  # ifOutErrors              16
                "2.1.2.2.1.21",  # ifOutQLen                17
                "4.1.11863.1.1.3.2.1.1.1.1.2",  # special for TP Link
                OIDBytes("2.1.2.2.1.6"),  # ifPhysAddress            19
                # Additionally fetch the standard OIDs for aliases.
                # Current tplink devices seem to support this OID and no longer the
                # ones under 4.1.11863.
                "2.1.31.1.1.1.18",  # ifAlias
            ],
        ),
    ],
    detect=all_of(contains(".1.3.6.1.2.1.1.2.0", ".4.1.11863."), if64.HAS_ifHCInOctets),
    supersedes=['if', 'if64'],
)

register.check_plugin(
    name="if64_tplink",
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

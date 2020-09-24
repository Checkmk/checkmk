#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import (
    all_of,
    equals,
    exists,
    OIDEnd,
    register,
    SNMPTree,
    type_defs,
)
from .utils import if64, interfaces


def parse_emc_vplex_if(string_table: type_defs.SNMPStringTable) -> interfaces.Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_emc_vplex_if([
    ... [['director-1-1-A', '128.221.252.35']],
    ... [['A0-FC00', '159850409786880', '118814791148032', '128.221.252.35.1']],
    ... []]))
    [Interface(index='1', descr='A0-FC00', alias='director-1-1-A A0-FC00', type='', speed=0, oper_status='1', in_octets=159850409786880, in_ucast=0, in_mcast=0, in_bcast=0, in_discards=0, in_errors=0, out_octets=118814791148032, out_ucast=0, out_mcast=0, out_bcast=0, out_discards=0, out_errors=0, out_qlen=0, phys_address='', oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None)]
    """
    directors = {}
    for director, ip in string_table[0]:
        directors[ip] = director

    return [
        interfaces.Interface(
            index=str(idx + 1),
            descr=frontend_info[0],
            alias="%s %s" % (directors[frontend_info[3].rsplit(".", 1)[0]], frontend_info[0]),
            type="",
            oper_status="1",
            in_octets=int(frontend_info[1]),
            out_octets=int(frontend_info[2]),
        ) for idx, frontend_info in enumerate(string_table[1] + string_table[2])
    ]


register.snmp_section(
    name="emc_vplex_if",
    parse_function=parse_emc_vplex_if,
    trees=[
        SNMPTree(
            base=".1.3.6.1.4.1.1139.21.2.2",
            oids=[
                "1.1.3",  # vplexDirectorName
                OIDEnd(),
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1139.21.2.2.5.1",
            oids=[
                "2",  # vplexDirectorFEPortName
                "9",  # vplexDirectorFEPortBytesRead
                "10",  # vplexDirectorFEPortBytesWrite
                OIDEnd(),
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1139.21.2.2.7.1",
            oids=[
                "2",  # vplexDirectorBEPortName
                "9",  # vplexDirectorBEPortBytesRead
                "10",  # vplexDirectorBEPortBytesWrite
                OIDEnd(),
            ],
        ),
    ],
    detect=all_of(
        equals(".1.3.6.1.2.1.1.1.0", ""),
        exists(".1.3.6.1.4.1.1139.21.2.2.8.1.*"),
    ),
    supersedes=['if', 'if64'],
)

register.check_plugin(
    name="emc_vplex_if",
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

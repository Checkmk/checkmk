#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping
from .agent_based_api.v1 import (
    register,
    Service,
    SNMPTree,
)
from .agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    Parameters,
    SNMPStringTable,
)
from .utils import huawei_osn, interfaces

Section = Mapping[str, interfaces.Interface]


def parse_huawei_osn_if(string_table: SNMPStringTable) -> Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_huawei_osn_if([[
    ... ['board=2,subcard=255,port=3,path=1', '7082029074219', '17036981', '279', '6838315476691', '17036419', '279', '3948539971896391', '7735753792855325', '310', '1283'],
    ... ['board=4,subcard=255,port=4,path=1', '6449739865058', '435114', '213', '17693276948796', '434014', '215', '1605155114074070', '22669531959919535', '0', '0'],
    ... ]]))
    {'board=2,subcard=255,port=3,path=1': Interface(index='board=2,subcard=255,port=3,path=1', descr='board=2,subcard=255,port=3,path=1', alias='board=2,subcard=255,port=3,path=1', type='39', speed=0, oper_status='1', in_octets=3948539971896391, in_ucast=7082029074219, in_mcast=17036981, in_bcast=279, in_discards=0, in_errors=310, out_octets=7735753792855325, out_ucast=6838315476691, out_mcast=17036419, out_bcast=279, out_discards=0, out_errors=1283, out_qlen=0, phys_address='', oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None),
     'board=4,subcard=255,port=4,path=1': Interface(index='board=4,subcard=255,port=4,path=1', descr='board=4,subcard=255,port=4,path=1', alias='board=4,subcard=255,port=4,path=1', type='39', speed=0, oper_status='1', in_octets=1605155114074070, in_ucast=6449739865058, in_mcast=435114, in_bcast=213, in_discards=0, in_errors=0, out_octets=22669531959919535, out_ucast=17693276948796, out_mcast=434014, out_bcast=215, out_discards=0, out_errors=0, out_qlen=0, phys_address='', oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None)}
    """
    return {
        name: interfaces.Interface(
            index=name,
            descr=name,
            alias=name,
            type='39',
            oper_status='1',
            in_octets=interfaces.saveint(line[7]),
            in_ucast=interfaces.saveint(line[1]),
            in_mcast=interfaces.saveint(line[2]),
            in_bcast=interfaces.saveint(line[3]),
            in_errors=interfaces.saveint(line[9]),
            out_octets=interfaces.saveint(line[8]),
            out_ucast=interfaces.saveint(line[4]),
            out_mcast=interfaces.saveint(line[5]),
            out_bcast=interfaces.saveint(line[6]),
            out_errors=interfaces.saveint(line[10]),
        ) for line in string_table[0] for name in [line[0]]
    }


register.snmp_section(
    name="huawei_osn_if",
    parse_function=parse_huawei_osn_if,
    trees=[
        SNMPTree(
            base=".1.3.6.1.4.1.2011.2.25.3.40.50.96.50.1",
            oids=[
                "3.200",  # OPTIX-GLOBAL-NGWDM-MIB::sdh_pathDataPmPara                   0
                "4.113",  # OPTIX-GLOBAL-NGWDM-MIB::sdh_pathDataPmMonValue.pmRXUNICAST   1
                "4.114",  # OPTIX-GLOBAL-NGWDM-MIB::sdh_pathDataPmMonValue.pmRXMULCAST   2
                "4.115",  # OPTIX-GLOBAL-NGWDM-MIB::sdh_pathDataPmMonValue.pmRXBRDCAST   3
                "4.116",  # OPTIX-GLOBAL-NGWDM-MIB::sdh_pathDataPmMonValue.pmTXUNICAST   4
                "4.117",  # OPTIX-GLOBAL-NGWDM-MIB::sdh_pathDataPmMonValue.pmTXMULCAST   5
                "4.118",  # OPTIX-GLOBAL-NGWDM-MIB::sdh_pathDataPmMonValue.pmTXBRDCAST   6
                "4.200",  # OPTIX-GLOBAL-NGWDM-MIB::sdh_pathDataPmMonValue.pmRXOCTETS    7
                "4.199",  # OPTIX-GLOBAL-NGWDM-MIB::sdh_pathDataPmMonValue.pmTXOCTETS    8
                "4.944",  # OPTIX-GLOBAL-NGWDM-MIB::sdh_pathDataPmMonValue.pmRXPBAD      9
                "4.945",  # OPTIX-GLOBAL-NGWDM-MIB::sdh_pathDataPmMonValue.pmTXPBAD     10
            ],
        ),
    ],
    detect=huawei_osn.SNMP_DETECT,
    supersedes=['if', 'if64'],
)


def discover_huawei_osn_if(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_huawei_osn_if(
    item: str,
    params: Parameters,
    section: Section,
) -> CheckResult:
    interface = section.get(item)
    if not interface:
        return
    yield from interfaces.check_single_interface(
        item,
        params,
        interface,
    )


register.check_plugin(
    name="huawei_osn_if",
    service_name="Interface %s",
    discovery_function=discover_huawei_osn_if,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_huawei_osn_if,
)

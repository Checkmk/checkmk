#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib import huawei, interfaces

Section = Mapping[str, interfaces.InterfaceWithCounters]


def parse_huawei_osn_if(string_table: Sequence[StringTable]) -> Section:
    return {
        name: interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index=name,
                descr=name,
                alias=name,
                type="39",
                oper_status="1",
            ),
            interfaces.Counters(
                in_octets=interfaces.saveint(line[7]),
                in_ucast=interfaces.saveint(line[1]),
                in_mcast=interfaces.saveint(line[2]),
                in_bcast=interfaces.saveint(line[3]),
                in_err=interfaces.saveint(line[9]),
                out_octets=interfaces.saveint(line[8]),
                out_ucast=interfaces.saveint(line[4]),
                out_mcast=interfaces.saveint(line[5]),
                out_bcast=interfaces.saveint(line[6]),
                out_err=interfaces.saveint(line[10]),
            ),
        )
        for line in string_table[0]
        for name in [line[0]]
    }


snmp_section_huawei_osn_if = SNMPSection(
    name="huawei_osn_if",
    parse_function=parse_huawei_osn_if,
    fetch=[
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
    detect=huawei.DETECT_HUAWEI_OSN,
    supersedes=["if", "if64"],
)


def discover_huawei_osn_if(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_huawei_osn_if(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    interface = section.get(item)
    if not interface:
        return
    yield from interfaces.check_single_interface(
        item,
        params,
        interfaces.InterfaceWithRatesAndAverages.from_interface_with_counters_or_rates(
            interface,
            timestamp=time.time(),
            value_store=get_value_store(),
            params=params,
        ),
    )


check_plugin_huawei_osn_if = CheckPlugin(
    name="huawei_osn_if",
    service_name="Interface %s",
    discovery_function=discover_huawei_osn_if,
    check_ruleset_name="interfaces",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_huawei_osn_if,
)

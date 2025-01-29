#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    exists,
    OIDEnd,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.poe import check_poe_data, PoeStatus, PoeValues

# We fetch the following columns from SNMP:
# 2 pethMainPsePower (The nominal power of the PSE expressed in Watts)
# 3 pethMainPseOperStatus (The operational status of the main PSE) (on(1), off(2), faulty(3))
# 4 pethMainPseConsumptionPower (Measured usage power expressed in Watts)


Section = Mapping[str, PoeValues]


def parse_pse_poe(string_table: StringTable) -> Section:
    """
    parse string_table data and create dictionary with namedtuples for each OID.

    {
       oid_end : PoeValues(poe_max, poe_used, poe_status, poe_status_detail)
    }

    :param string_table: parsed snmp data
    :return: dictionary
    """
    poe_dict = {}
    for oid_end, poe_max, pse_op_status, poe_used in string_table:
        if not poe_max or not pse_op_status or not poe_used:
            continue
        poe_dict[str(oid_end)] = PoeValues(
            poe_max=int(poe_max),
            poe_used=int(poe_used),
            poe_status=PoeStatus(int(pse_op_status)),
            poe_status_detail=None,
        )
    return poe_dict


def discover_pse_poe(section: Section) -> DiscoveryResult:
    yield from [Service(item=oid_end) for oid_end in section]


def check_pse_poe(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (poe_data := section.get(item)):
        return
    yield from check_poe_data(params, poe_data)


snmp_section_pse_poe = SimpleSNMPSection(
    name="pse_poe",
    detect=exists(".1.3.6.1.2.1.105.1.3.1.1.*"),
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.105.1.3.1.1",
        oids=[OIDEnd(), "2", "3", "4"],
    ),
    parse_function=parse_pse_poe,
)
check_plugin_pse_poe = CheckPlugin(
    name="pse_poe",
    service_name="POE%s consumption ",
    discovery_function=discover_pse_poe,
    check_function=check_pse_poe,
    check_default_parameters={"levels": ("fixed", (90.0, 95.0))},
)

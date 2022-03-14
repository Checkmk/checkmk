#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, Mapping

from .agent_based_api.v1 import register, SNMPTree, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable
from .utils.perle import DETECT_PERLE

# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.2.1.1 1 --> PERLE-MCR-MGT-MIB::mcrPsmuIndex.1.a
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.2.1.2 2 --> PERLE-MCR-MGT-MIB::mcrPsmuIndex.1.b
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.3.1.1 MCR-ACPWR --> PERLE-MCR-MGT-MIB::mcrPsmuModelName.1.a
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.3.1.2 MCR-ACPWR --> PERLE-MCR-MGT-MIB::mcrPsmuModelName.1.b
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.4.1.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.4.1.2
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.5.1.1 104-101015T10175 --> PERLE-MCR-MGT-MIB::mcrPsmuPsuSerialNumber.1.a
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.5.1.2 104-101015T10177 --> PERLE-MCR-MGT-MIB::mcrPsmuPsuSerialNumber.1.b
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.9.1.1 1 --> PERLE-MCR-MGT-MIB::mcrPsmuPsuStatus.1.a
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.9.1.2 1 --> PERLE-MCR-MGT-MIB::mcrPsmuPsuStatus.1.b
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.10.1.1 12.05 --> PERLE-MCR-MGT-MIB::mcrPsmuPsuVoltage.1.a
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.10.1.2 12.05 --> PERLE-MCR-MGT-MIB::mcrPsmuPsuVoltage.1.b
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.11.1.1 6.75 --> PERLE-MCR-MGT-MIB::mcrPsmuPsuPowerUsage.1.a
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.11.1.2 6.75 --> PERLE-MCR-MGT-MIB::mcrPsmuPsuPowerUsage.1.b
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.12.1.1 1 --> PERLE-MCR-MGT-MIB::mcrPsmuFanStatus.1.a
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.12.1.2 1 --> PERLE-MCR-MGT-MIB::mcrPsmuFanStatus.1.b

Section = Mapping[str, Mapping[str, Any]]

_MAP_STATES = {
    "0": (2, "not present"),
    "1": (0, "good"),
    "2": (2, "fail"),
}


def parse_perle_psmu(string_table: StringTable) -> Section:
    parsed: Dict[str, Dict[str, Any]] = {}
    for (
        index,
        modelname,
        descr,
        serial,
        psu_status,
        voltage_str,
        power_str,
        fan_status,
    ) in string_table:
        parsed.setdefault(
            index,
            {
                "model": modelname,
                "descr": descr,
                "serial": serial,
                "fanstate": _MAP_STATES.get(fan_status, (3, "unknown[%s]" % fan_status)),
                "psustate": _MAP_STATES.get(psu_status, (3, "unknown[%s]" % psu_status)),
            },
        )
        for what, value_str in [("power", power_str), ("voltage", voltage_str)]:
            try:
                parsed[index].setdefault(what, float(value_str))
            except ValueError:
                pass

    return parsed


register.snmp_section(
    name="perle_psmu",
    parse_function=parse_perle_psmu,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1966.21.1.1.1.1.2.1",
        oids=[
            "2",  # PERLE-MCR-MGT-MIB::mcrPsmuIndex
            "3",  # PERLE-MCR-MGT-MIB::mcrPsmuModelName
            "4",  # PERLE-MCR-MGT-MIB::mcrPsmuModelDesc
            "5",  # PERLE-MCR-MGT-MIB::mcrPsmuPsuSerialNumber
            "9",  # PERLE-MCR-MGT-MIB::mcrPsmuPsuStatus
            "10",  # PERLE-MCR-MGT-MIB::mcrPsmuPsuVoltageUsage
            "11",  # PERLE-MCR-MGT-MIB::mcrPsmuPsuPowerUsage
            "12",  # PERLE-MCR-MGT-MIB::mcrPsmuFanStatus
        ],
    ),
    detect=DETECT_PERLE,
)


def inventory_perle_psmu(section: Section) -> InventoryResult:
    for psu_index, data in section.items():
        yield TableRow(
            path=["hardware", "components", "psus"],
            key_columns={
                "index": psu_index,
            },
            inventory_columns={
                "description": data["descr"],
                "model": data["model"],
                "serial": data["serial"],
            },
            status_columns={},
        )


register.inventory_plugin(
    name="perle_psmu",
    inventory_function=inventory_perle_psmu,
)

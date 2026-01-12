#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.3652.3.2.1.1.0 M9-2 --> SPEEDCARRIER-MIB::nmCarrierName.0
# .1.3.6.1.4.1.3652.3.2.1.2.0 4 --> SPEEDCARRIER-MIB::nmCarrierType.0
# .1.3.6.1.4.1.3652.3.2.1.3.0 3 --> SPEEDCARRIER-MIB::nmPSU1Status.0
# .1.3.6.1.4.1.3652.3.2.1.4.0 3 --> SPEEDCARRIER-MIB::nmPSU2Status.0
# .1.3.6.1.4.1.3652.3.2.1.5.0 3 --> SPEEDCARRIER-MIB::nmFanState.0
# .1.3.6.1.4.1.3652.3.2.1.6.0 8 --> SPEEDCARRIER-MIB::nmCarrierPSU1Type.0
# .1.3.6.1.4.1.3652.3.2.1.7.0 8 --> SPEEDCARRIER-MIB::nmCarrierPSU2Type.0
# .1.3.6.1.4.1.3652.3.2.1.8.0 --> SPEEDCARRIER-MIB::nmCarrierPSU1Text.0
# .1.3.6.1.4.1.3652.3.2.1.9.0 --> SPEEDCARRIER-MIB::nmCarrierPSU2Text.0
# .1.3.6.1.4.1.3652.3.2.1.10.0 --> SPEEDCARRIER-MIB::nmCarrierPSU3Text.0
# .1.3.6.1.4.1.3652.3.2.1.11.0 0 --> SPEEDCARRIER-MIB::nmCarrierPSU3Type.0
# .1.3.6.1.4.1.3652.3.2.1.12.0 0 --> SPEEDCARRIER-MIB::nmPSU3Status.0


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.pandacom.lib import DETECT_PANDACOM

Section = Mapping[str, Mapping[str, Any]]


def parse_pandacom_psu(string_table: StringTable) -> Section | None:
    map_psu_type = {
        "0": "type not configured",
        "1": "230 V AC 75 W",
        "2": "230 V AC 160 W",
        "3": "48 V DC 75 W",
        "4": "48 V DC 150 W",
        "5": "48 V DC 60 W",
        "6": "230 V AC 60 W",
        "7": "48 V DC 250 W",
        "8": "230 V AC 250 W",
        "9": "48 V DC 1100 W",
        "10": "230 V AC 1100 W",
        "255": "type not available",
        "65025": "48 V DC 60 W",
        "65026": "230 V AC 60 W",
        "65027": "48 V DC 250 W",
        "65028": "230 V AC 250 W",
        "65029": "48 V DC 1100 W",
        "65030": "230 V AC 1100 W",
        "65031": "48 V DC 1100 W 1 UH",
        "65032": "230 V AC 1100 W 1 UH",
        "65033": "230 V AC 1200W 1 UH",
    }
    map_psu_state = {
        "0": (State.UNKNOWN, "not installed"),
        "1": (State.CRIT, "fail"),
        "2": (State.WARN, "temperature warning"),
        "3": (State.OK, "pass"),
        "255": (State.UNKNOWN, "not available"),
    }

    if not string_table:
        return None

    parsed = {}
    for psu_nr, type_index, state_index in [
        ("1", 5, 2),
        ("2", 6, 3),
        ("3", 10, 11),
    ]:
        if string_table[state_index][0] not in ["0", "255"]:
            parsed[psu_nr] = {
                "type": map_psu_type[string_table[type_index][0]],
                "state": map_psu_state[string_table[state_index][0]],
            }

    return parsed


def discover_pandacom_psu(section: Section) -> DiscoveryResult:
    for psu_nr in section:
        yield Service(item=psu_nr)


def check_pandacom_psu(item: str, section: Section) -> CheckResult:
    if item in section:
        state, state_readable = section[item]["state"]
        yield Result(
            state=state,
            summary=f"[{section[item]['type']}] Operational status: {state_readable}",
        )


snmp_section_pandacom_psu = SimpleSNMPSection(
    name="pandacom_psu",
    detect=DETECT_PANDACOM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3652.3.2",
        oids=["1"],
    ),
    parse_function=parse_pandacom_psu,
)


check_plugin_pandacom_psu = CheckPlugin(
    name="pandacom_psu",
    service_name="Power Supply %s",
    discovery_function=discover_pandacom_psu,
    check_function=check_pandacom_psu,
)

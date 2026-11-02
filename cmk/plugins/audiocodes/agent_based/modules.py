#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    InventoryPlugin,
    InventoryResult,
    OIDEnd,
    SNMPSection,
    SNMPTree,
    StringTable,
    TableRow,
)

from .lib import DETECT_AUDIOCODES, MODULE_TYPE_MAPPING, parse_license_key_list

acSysRedundantModuleTypeMapping = {
    "0": "acUnknown",
    "73": "acMediantSW",
    "79": "acMediant-VE-SBC",
    "80": "acMediant-VE-H-SBC",
    "81": "acMediant-SE-SBC",
    "82": "acMediant-SE-H-SBC",
    "83": "acMediant-9000-SBC",
    "84": "acMediant-500L-MSBR",
    "85": "acMediant-500L-ESBC",
    "265": "acMediant800CPUmodule",
    "266": "acMediant800IFDigitalModule",
    "267": "acMediant800IFAnalogModule",
    "268": "acMediant800IFBRIModule",
    "272": "acMediant800EthernetModule",
    "280": "acMediant4000CPUmodule",
    "283": "acMediant500CPUmodule",
    "284": "acMediant500IFDigitalModule",
    "285": "acMediant500IFAnalogModule",
    "286": "acMediant500IFBRIModule",
    "290": "acMediant500EthernetModule",
    "295": "acMediant4000MPModule",
    "308": "acMediant2600CPUmodule",
    "309": "acMediant2600MPModule",
}

HaStatusMapping = {
    "0": "Invalid status",
    "1": "Active - no HA",
    "2": "Active",
    "3": "Redundant",
    "4": "Stand alone",
    "5": "Redundant - no HA",
    "6": "Not applicable",
}


@dataclass(frozen=True, kw_only=True)
class Module:
    index: str  # Needed to key on when creating the inventory table
    type: str
    serial_number: str
    ha_status: str
    sw_version: str
    license_key_list: str


@dataclass(frozen=True, kw_only=True)
class Section:
    modules: Sequence[Module]
    redundant_modules: Sequence[Module]


def parse_audiocodes_modules(string_table: Sequence[StringTable]) -> Section | None:
    if not string_table[0] and not string_table[1]:
        return None

    return Section(
        modules=_parse_ac_sys_modules(
            string_table[0],
            MODULE_TYPE_MAPPING,
            HaStatusMapping,
        ),
        redundant_modules=_parse_ac_sys_modules(
            string_table[1],
            acSysRedundantModuleTypeMapping,
            HaStatusMapping,
        ),
    )


def _parse_ac_sys_modules(
    string_table: StringTable,
    type_mapping: Mapping[str, str],
    ha_status_mapping: Mapping[str, str],
) -> Sequence[Module]:
    return [
        Module(
            index=module[0],
            type=type_mapping.get(module[1], module[1]),
            serial_number=module[2],
            ha_status=ha_status_mapping.get(module[3], module[3]),
            sw_version=module[4],
            license_key_list=parse_license_key_list(module[5]),
        )
        for module in string_table
    ]


snmp_section_audiocodes_modules = SNMPSection(
    name="audiocodes_modules",
    supersedes=["snmp_extended_info"],
    detect=DETECT_AUDIOCODES,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.5003.9.10.10.4.21.1",
            oids=[OIDEnd(), "3", "6", "9", "7", "5"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5003.9.10.10.4.27.21.1",
            oids=[OIDEnd(), "3", "6", "9", "7", "5"],
        ),
    ],
    parse_function=parse_audiocodes_modules,
)


def inventory_audiocodes_modules(section: Section) -> InventoryResult:
    for module in [*section.modules, *section.redundant_modules]:
        yield TableRow(
            path=["hardware", "components", "modules"],
            key_columns={"index": module.index},
            inventory_columns={
                "type": module.type,
                "serial": module.serial_number,
                "ha_status": module.ha_status,
                "software_version": module.sw_version,
                "license_key_list": module.license_key_list,
            },
        )


inventory_plugin_audiocodes_modules = InventoryPlugin(
    name="audiocodes_modules",
    inventory_function=inventory_audiocodes_modules,
)

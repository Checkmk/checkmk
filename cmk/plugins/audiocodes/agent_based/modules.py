#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    InventoryPlugin,
    InventoryResult,
    SNMPSection,
    SNMPTree,
    StringTable,
    TableRow,
)

from .lib import DETECT_AUDIOCODES, parse_license_key_list

acSysModuleTypeMapping = {
    "0": "acUnknown",
    "1": "acTrunkPack-08",
    "2": "acMediaPack-108",
    "3": "acMediaPack-124",
    "20": "acTrunkPack-1600",
    "22": "acTPM1100",
    "23": "acTrunkPack-260-IpMedia",
    "24": "acTrunkPack-1610",
    "25": "acMediaPack-104",
    "26": "acMediaPack-102",
    "29": "acTrunkPack-1610-SB",
    "30": "acTrunkPack-1610-IpMedia",
    "31": "acTrunkPack-MEDIANT2000",
    "32": "acTrunkPack-STRETTO2000",
    "33": "acTrunkPack-IPMServer2000",
    "34": "acTrunkPack-2810",
    "36": "acTrunkPack-260-IpMedia-30Ch",
    "37": "acTrunkPack-260-IpMedia-60Ch",
    "38": "acTrunkPack-260-IpMedia-120Ch",
    "39": "acTrunkPack-260RT-IpMedia-30Ch",
    "40": "acTrunkPack-260RT-IpMedia-60Ch",
    "41": "acTrunkPack-260RT-IpMedia-120Ch",
    "42": "acTrunkPack-260",
    "44": "acTPM1100-PCM",
    "45": "acTrunkPack-6310",
    "46": "acTPM6300",
    "47": "acMediant1000",
    "48": "acIPMedia3000",
    "49": "acMediant3000",
    "50": "acStretto3000",
    "51": "acTrunkPack-6310-IpMedia",
    "52": "acTrunkPack-6310-SB",
    "53": "acATP-1610",
    "54": "acATP-260",
    "55": "acATP-260-UN",
    "56": "acMediaPack-118",
    "57": "acMediaPack114",
    "58": "acMediaPack112",
    "59": "acTrunkPack-6310-T3",
    "60": "acMediant3000-T3",
    "61": "acIPmedia3000-T3",
    "62": "acTrunkPack-6310-T3-IpMedia",
    "63": "acTrunkPack-8410",
    "64": "acTrunkPack-8410-IpMedia",
    "69": "acMediant-800-MSBR",
    "70": "acMediant-4000",
    "71": "acMediant-1000-ESBC",
    "72": "acMediaPack-500-ESBC",
    "73": "acMediantSW",
    "74": "acMediant-800B-MSBG",
    "75": "acMediant-800B-ESBC",
    "76": "acMediant-500-MSBG",
    "77": "acMediant-500-ESBC",
    "78": "acMediant-2600",
    "79": "acMediant-VE-SBC",
    "80": "acMediant-VE-H-SBC",
    "81": "acMediant-SE-SBC",
    "82": "acMediant-SE-H-SBC",
    "83": "acMediant-9000-SBC",
    "84": "acMediant-500L-MSBR",
    "85": "acMediant-500L-ESBC",
    "250": "sA1",
    "251": "sA2",
    "252": "sA3",
    "253": "acMediant1000CPUmodule",
    "254": "acMediant1000IFDigitalModule",
    "255": "acMediant1000IFAnalogModule",
    "256": "acMediant1000IFBRIModule",
    "257": "acMediant1000IPMediaModule",
    "258": "acMediant600CPUmodule",
    "259": "acMediant600IFDigitalModule",
    "260": "acMediant600IFAnalogModule",
    "261": "acMediant600IFBRIModule",
    "262": "acMediant600IPMediaModule",
    "265": "acMediant800CPUmodule",
    "266": "acMediant800IFDigitalModule",
    "267": "acMediant800IFAnalogModule",
    "268": "acMediant800IFBRIModule",
    "269": "acMediant800IFWANModule",
    "270": "acMediant800IFWiFiModule",
    "271": "acMediant800IPMediaModule",
    "272": "acMediant800EthernetModule",
    "273": "acMediant800IFT1WANModule",
    "274": "acMediant800IFSHDSLModule",
    "275": "acMediant800IFADSLModule",
    "276": "acMediant1000IFWANModule",
    "277": "acMediant1000IFT1WANModule",
    "278": "acMediant1000IFSHDSLModule",
    "279": "acMediant1000IFADSLModule",
    "280": "acMediant4000CPUmodule",
    "281": "acMediant1000EthernetModule",
    "282": "acSWESBCModule",
    "283": "acMediant500CPUmodule",
    "284": "acMediant500IFDigitalModule",
    "285": "acMediant500IFAnalogModule",
    "286": "acMediant500IFBRIModule",
    "287": "acMediant500IFWANModule",
    "288": "acMediant500IFWiFiModule",
    "289": "acMediant500IPMediaModule",
    "290": "acMediant500EthernetModule",
    "291": "acMediant500IFT1WANModule",
    "292": "acMediant500IFSHDSLModule",
    "293": "acMediant500IFADSLModule",
    "294": "acMediant500IFGESFPModule",
    "295": "acMediant4000MPModule",
    "296": "acMediant-800B-MSBR",
    "297": "acMediant800BCPUmodule",
    "298": "acMediant800BIFDigitalModule",
    "299": "acMediant800BIFAnalogModule",
    "300": "acMediant800BIFBRIModule",
    "301": "acMediant800BIFWANModule",
    "302": "acMediant800BIFWiFiModule",
    "303": "acMediant800BIPMediaModule",
    "304": "acMediant800BEthernetModule",
    "305": "acMediant800BIFT1WANModule",
    "306": "acMediant800BIFSHDSLModule",
    "307": "acMediant800BIFADSLModule",
    "308": "acMediant2600CPUmodule",
    "309": "acMediant2600MPModule",
    "310": "acMediaPack1288CPUmodule",
    "311": "acMediaPack1288FXSAnalogModule",
    "312": "acMediaPack1288FXOAnalogModule",
}

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
            acSysModuleTypeMapping,
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
            type=type_mapping.get(module[0], module[0]),
            serial_number=module[1],
            ha_status=ha_status_mapping.get(module[2], module[2]),
            sw_version=module[3],
            license_key_list=parse_license_key_list(module[4]),
        )
        for module in string_table
    ]


snmp_section_audiocodes_modules = SNMPSection(
    name="audiocodes_modules",
    detect=DETECT_AUDIOCODES,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.5003.9.10.10.4.21.1",
            oids=["3", "6", "9", "7", "5"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5003.9.10.10.4.27.21.1",
            oids=["3", "6", "9", "7", "5"],
        ),
    ],
    parse_function=parse_audiocodes_modules,
)


def inventory_audiocodes_modules(section: Section) -> InventoryResult:
    for module in [*section.modules, *section.redundant_modules]:
        yield TableRow(
            path=["hardware", "components", "modules"],
            key_columns={"type": module.type},
            inventory_columns={
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

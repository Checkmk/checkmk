#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeVar

from cmk.agent_based.v2 import CheckResult, contains, Result, State, StringTable

DETECT_AUDIOCODES = contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5003.8.1.1")

MODULE_TYPE_MAPPING = {
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

T = TypeVar("T")


def data_by_item(
    section_audiocodes_module_names: Mapping[str, str],
    data_section: Mapping[str, T],
) -> dict[str, T]:
    return {
        f"{name} {index}": data
        for index, data in data_section.items()
        if (name := section_audiocodes_module_names.get(index)) is not None
    }


@dataclass(frozen=True, kw_only=True)
class OPState:
    name: str
    state: State


@dataclass(frozen=True, kw_only=True)
class Presence:
    name: str
    state: State


@dataclass(frozen=True, kw_only=True)
class HAStatus:
    name: str
    state: State


OPERATIONAL_STATE_MAPPING = {
    "0": OPState(name="Invalid state", state=State.CRIT),
    "1": OPState(name="Disabled", state=State.CRIT),
    "2": OPState(name="Enabled", state=State.OK),
}
PRESENCE_MAPPING = {
    "0": Presence(name="Invalid status", state=State.CRIT),
    "1": Presence(name="Module present", state=State.OK),
    "2": Presence(name="Module missing", state=State.CRIT),
}

HA_STATUS_MAPPING = {
    "0": HAStatus(name="Invalid status", state=State.CRIT),
    "1": HAStatus(name="Active - no HA", state=State.WARN),
    "2": HAStatus(name="Active", state=State.OK),
    "3": HAStatus(name="Redundant", state=State.OK),
    "4": HAStatus(name="Stand alone", state=State.OK),
    "5": HAStatus(name="Redundant - no HA", state=State.WARN),
    "6": HAStatus(name="Not applicable", state=State.OK),
}


@dataclass(frozen=True, kw_only=True)
class Module:
    op_state: OPState
    presence: Presence
    ha_status: HAStatus


def parse_audiocodes_operational_state(
    string_table: StringTable,
) -> Mapping[str, Module] | None:
    if not string_table:
        return None

    return {
        module[0]: Module(
            op_state=OPERATIONAL_STATE_MAPPING[module[1]],
            presence=PRESENCE_MAPPING[module[2]],
            ha_status=HA_STATUS_MAPPING[module[3]],
        )
        for module in string_table
    }


def check_audiocodes_operational_state(module: Module) -> CheckResult:
    yield Result(
        state=module.op_state.state,
        summary=f"Operational state: {module.op_state.name}",
    )
    yield Result(
        state=module.presence.state,
        notice=f"Presence: {module.presence.name}",
    )
    yield Result(
        state=module.ha_status.state,
        summary=f"HA status: {module.ha_status.name}",
    )


def parse_license_key_list(license_key_list: str) -> str:
    try:
        return bytes.fromhex(license_key_list.replace(" ", "")).decode("utf-8")
    except ValueError:
        return license_key_list

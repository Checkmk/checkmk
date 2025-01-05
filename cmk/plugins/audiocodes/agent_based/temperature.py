#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamDict

from .lib import data_by_item, DETECT_AUDIOCODES


def parse_audiocodes_temperature(string_table: StringTable) -> Mapping[str, float] | None:
    if not string_table:
        return None

    return {module[0]: float(module[1]) for module in string_table}


snmp_section_audiocodes_temperature = SimpleSNMPSection(
    name="audiocodes_temperature",
    detect=DETECT_AUDIOCODES,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5003.9.10.10.4.21.1",
        oids=[
            OIDEnd(),
            "11",  # acSysModuleTemperature
        ],
    ),
    parse_function=parse_audiocodes_temperature,
)


def discover_audiocodes_temperature(
    section_audiocodes_module_names: Mapping[str, str] | None,
    section_audiocodes_temperature: Mapping[str, float] | None,
) -> DiscoveryResult:
    if not section_audiocodes_module_names or not section_audiocodes_temperature:
        return

    yield from (
        Service(item=item)
        for item in data_by_item(
            section_audiocodes_module_names,
            section_audiocodes_temperature,
        )
    )


def check_audiocodes_temperature(
    item: str,
    params: TempParamDict,
    section_audiocodes_module_names: Mapping[str, str] | None,
    section_audiocodes_temperature: Mapping[str, float] | None,
) -> CheckResult:
    if not section_audiocodes_temperature or not section_audiocodes_module_names:
        return

    if (
        module_temp := data_by_item(
            section_audiocodes_module_names,
            section_audiocodes_temperature,
        ).get(item)
    ) is None:
        return

    if module_temp == -1:
        yield Result(
            state=State.OK,
            summary="Temperature is not available",
        )
        return

    yield from check_temperature(
        reading=module_temp,
        params=params,
    )


check_plugin_audiocodes_temperature = CheckPlugin(
    name="audiocodes_temperature",
    service_name="AudioCodes Temperature %s",
    sections=["audiocodes_module_names", "audiocodes_temperature"],
    discovery_function=discover_audiocodes_temperature,
    check_function=check_audiocodes_temperature,
    check_default_parameters={},
    check_ruleset_name="temperature",
)

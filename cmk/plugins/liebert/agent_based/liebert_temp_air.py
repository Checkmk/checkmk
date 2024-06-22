#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import MutableMapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.liebert.agent_based.lib import (
    DETECT_LIEBERT,
    parse_liebert,
    Section,
    SystemSection,
    temperature_to_celsius,
)

ParsedSection = Section[str]


def _get_item_from_key(key: str) -> str:
    return key.replace(" Air Temperature", "")


def _get_item_data(item: str, section_liebert_temp_air: ParsedSection) -> tuple[str, str] | None:
    for key, data in section_liebert_temp_air.items():
        if _get_item_from_key(key) == item:
            return data
    return None


def parse_liebert_temp_air(string_table: Sequence[StringTable]) -> ParsedSection:
    return parse_liebert(string_table, str)


def discover_liebert_temp_air(
    section_liebert_temp_air: ParsedSection | None,
    section_liebert_system: SystemSection | None,
) -> DiscoveryResult:
    if not section_liebert_temp_air:
        return
    for key, (value, _unit) in section_liebert_temp_air.items():
        if "Unavailable" not in value:
            yield Service(item=_get_item_from_key(key))


def check_liebert_temp_air(
    item: str,
    params: TempParamType,
    section_liebert_temp_air: ParsedSection | None,
    section_liebert_system: SystemSection | None,
) -> CheckResult:
    value_store = get_value_store()
    yield from _check_liebert_temp_air(
        item,
        params,
        section_liebert_temp_air,
        section_liebert_system,
        value_store,
    )


def _check_liebert_temp_air(
    item: str,
    params: TempParamType,
    section_liebert_temp_air: ParsedSection | None,
    section_liebert_system: SystemSection | None,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    if section_liebert_temp_air is None or section_liebert_system is None:
        return

    if not (item_data := _get_item_data(item, section_liebert_temp_air)):
        return

    value, unit = item_data

    device_state = section_liebert_system.get("Unit Operating State")
    if "Unavailable" in value and device_state == "standby":
        yield Result(state=State.OK, summary="Unit is in standby (unavailable)")
        return

    try:
        value_float = float(value)
    except ValueError:
        return

    yield from check_temperature(
        temperature_to_celsius(value_float, unit),
        params,
        unique_name="check_liebert_temp_air.%s" % item,
        value_store=value_store,
    )


snmp_section_liebert_temp_air = SNMPSection(
    name="liebert_temp_air",
    detect=DETECT_LIEBERT,
    parse_function=parse_liebert_temp_air,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
            oids=[
                "10.1.2.1.4291",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryDataLabel
                "20.1.2.1.4291",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryValue
                "30.1.2.1.4291",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryUnitsOfMeasure
                "10.1.2.1.5002",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryDataLabel
                "20.1.2.1.5002",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryValue
                "30.1.2.1.5002",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryUnitsOfMeasure
            ],
        ),
    ],
)

check_plugin_liebert_temp_air = CheckPlugin(
    name="liebert_temp_air",
    sections=["liebert_temp_air", "liebert_system"],
    service_name="%s Temperature",
    check_default_parameters={},
    discovery_function=discover_liebert_temp_air,
    check_function=check_liebert_temp_air,
    check_ruleset_name="temperature",
)

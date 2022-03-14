#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List, MutableMapping, Optional, Tuple

from .agent_based_api.v1 import get_value_store, register, Result, Service, SNMPTree
from .agent_based_api.v1 import State as state
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.liebert import DETECT_LIEBERT, parse_liebert
from .utils.temperature import check_temperature, TempParamType, to_celsius

ParsedSection = Dict[str, Any]


def _get_item_from_key(key: str) -> str:
    return key.replace(" Air Temperature", "")


def _get_item_data(item: str, section_liebert_temp_air: ParsedSection) -> Tuple:
    for key, data in section_liebert_temp_air.items():
        if _get_item_from_key(key) == item:
            return data
    return (None, None)


def parse_liebert_temp_air(string_table: List[StringTable]) -> ParsedSection:
    return parse_liebert(string_table, str)


def discover_liebert_temp_air(
    section_liebert_temp_air: Optional[ParsedSection],
    section_liebert_system: Optional[Dict[str, str]],
) -> DiscoveryResult:
    if not section_liebert_temp_air:
        return
    for key, (value, _unit) in section_liebert_temp_air.items():
        if "Unavailable" not in value:
            yield Service(item=_get_item_from_key(key))


def check_liebert_temp_air(
    item: str,
    params: TempParamType,
    section_liebert_temp_air: Optional[ParsedSection],
    section_liebert_system: Optional[Dict[str, str]],
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
    section_liebert_temp_air: Optional[ParsedSection],
    section_liebert_system: Optional[Dict[str, str]],
    value_store: MutableMapping[str, Any],
) -> CheckResult:

    if section_liebert_temp_air is None or section_liebert_system is None:
        return

    value, unit = _get_item_data(item, section_liebert_temp_air)
    if value is None:
        return

    device_state = section_liebert_system.get("Unit Operating State")
    if "Unavailable" in value and device_state == "standby":
        yield Result(state=state.OK, summary="Unit is in standby (unavailable)")
        return

    try:
        value = float(value)
    except ValueError:
        return

    unit = unit.replace("deg ", "").lower()
    value = to_celsius(value, unit)
    yield from check_temperature(
        value,
        params,
        unique_name="check_liebert_temp_air.%s" % item,
        value_store=value_store,
    )


register.snmp_section(
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

register.check_plugin(
    name="liebert_temp_air",
    sections=["liebert_temp_air", "liebert_system"],
    service_name="%s Temperature",
    check_default_parameters={},
    discovery_function=discover_liebert_temp_air,
    check_function=check_liebert_temp_air,
    check_ruleset_name="temperature",
)

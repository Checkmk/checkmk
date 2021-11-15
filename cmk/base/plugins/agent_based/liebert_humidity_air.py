#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# example output
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5027 Supply Humidity
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5027 Unavailable
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5027 % RH
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5028 Return Humidity
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5028 21.0
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5028 % RH

from typing import Any, Dict, List, Mapping, Optional, Tuple

from .agent_based_api.v1 import check_levels, register, Result, Service, SNMPTree
from .agent_based_api.v1 import State as state
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.liebert import DETECT_LIEBERT, parse_liebert

LIEBERT_HUMIDITY_AIR_DEFAULT_PARAMETERS = {
    "levels": (50, 55),
    "levels_lower": (10, 15),
}

ParsedSection = Dict[str, Any]


def _item_from_key(key: str) -> str:
    return key.replace(" Humidity", "")


def _get_item_data(
    item: str,
    section: ParsedSection,
) -> Tuple:
    for key, data in section.items():
        if _item_from_key(key) == item:
            return data
    return (None, None)


def parse_liebert_humidity_air(string_table: List[StringTable]) -> ParsedSection:
    return parse_liebert(string_table, str)


def discover_liebert_humidity_air(
    section_liebert_humidity_air: Optional[ParsedSection],
    section_liebert_system: Optional[Dict[str, str]],
) -> DiscoveryResult:

    if section_liebert_humidity_air is None:
        return

    for key, (value, _unit) in section_liebert_humidity_air.items():
        if "Unavailable" not in value:
            yield Service(item=_item_from_key(key))


def check_liebert_humidity_air(
    item: str,
    params: Mapping[str, Any],
    section_liebert_humidity_air: Optional[ParsedSection],
    section_liebert_system: Optional[Dict[str, str]],
) -> CheckResult:

    if section_liebert_humidity_air is None or section_liebert_system is None:
        return

    value, unit = _get_item_data(item, section_liebert_humidity_air)
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

    yield from check_levels(
        value=value,
        metric_name="humidity",
        levels_upper=params["levels"],
        levels_lower=params["levels_lower"],
        render_func=lambda retval: "%.2f %s" % (retval, unit),
        boundaries=(0, None),
    )


register.snmp_section(
    name="liebert_humidity_air",
    detect=DETECT_LIEBERT,
    parse_function=parse_liebert_humidity_air,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
            oids=[
                "10.1.2.1.5027",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryDataLabel
                "20.1.2.1.5027",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryValue
                "30.1.2.1.5027",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryUnitsOfMeasure
                "10.1.2.1.5028",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryDataLabel
                "20.1.2.1.5028",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryValue
                "30.1.2.1.5028",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryUnitsOfMeasure
            ],
        ),
    ],
)

register.check_plugin(
    name="liebert_humidity_air",
    sections=["liebert_humidity_air", "liebert_system"],
    service_name="%s Humidity",
    discovery_function=discover_liebert_humidity_air,
    check_function=check_liebert_humidity_air,
    check_default_parameters=LIEBERT_HUMIDITY_AIR_DEFAULT_PARAMETERS,
    check_ruleset_name="humidity",
)

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamDict
from cmk.plugins.liebert.agent_based.lib import (
    DETECT_LIEBERT,
    parse_liebert,
    temperature_to_celsius,
)


@dataclasses.dataclass(frozen=True)
class Section:
    readings: Mapping[str, float]
    upper_device_levels: tuple[float, float] | None
    lower_device_levels: tuple[float, float] | None


def parse_liebert_temp_fluid(string_table: StringTable) -> Section:
    pre_parsed = {
        name: temperature_to_celsius(reading, unit)
        for name, (reading, unit) in parse_liebert([string_table], float).items()
    }

    upper_warn = pre_parsed.pop("Supply Fluid Over Temp Alarm Threshold", None)
    upper_crit = pre_parsed.pop("Supply Fluid Over Temp Warning Threshold", None)
    lower_warn = pre_parsed.pop("Supply Fluid Under Temp Alarm Threshold", None)
    lower_crit = pre_parsed.pop("Supply Fluid Under Temp Warning Threshold", None)

    if upper_warn is not None and upper_crit is not None:
        if 0 in (upper_warn, upper_crit):
            upper_warn = max(upper_warn, upper_crit)
            upper_crit = upper_warn
        upper_levels = (upper_warn, upper_crit)
    else:
        upper_levels = None

    return Section(
        readings=pre_parsed,
        upper_device_levels=upper_levels,
        lower_device_levels=(
            (lower_warn, lower_crit) if lower_warn is not None and lower_crit is not None else None
        ),
    )


snmp_section_liebert_temp_fluid = SimpleSNMPSection(
    name="liebert_temp_fluid",
    detect=DETECT_LIEBERT,
    parse_function=parse_liebert_temp_fluid,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
        oids=[
            "10.1.2.1.5283",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryDataLabel
            "20.1.2.1.5283",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryValue
            "30.1.2.1.5283",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryUnitsOfMeasure
            "10.1.2.1.5284",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryDataLabel
            "20.1.2.1.5284",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryValue
            "30.1.2.1.5284",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryUnitsOfMeasure
            "10.1.2.1.5285",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryDataLabel
            "20.1.2.1.5285",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryValue
            "30.1.2.1.5285",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryUnitsOfMeasure
            "10.1.2.1.5286",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryDataLabel
            "20.1.2.1.5286",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryValue
            "30.1.2.1.5286",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryUnitsOfMeasure
            "10.1.2.1.5287",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryDataLabel
            "20.1.2.1.5287",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryValue
            "30.1.2.1.5287",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryUnitsOfMeasure
            "10.1.2.2.4644",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryDataLabel
            "20.1.2.2.4644",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryValue
            "30.1.2.2.4644",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryUnitsOfMeasure
        ],
    ),
)


def discover_liebert_temp_fluid(section: Section) -> DiscoveryResult:
    yield from (Service(item=name) for name in section.readings if "Set Point" in name)


def check_liebert_temp_fluid(item: str, params: TempParamDict, section: Section) -> CheckResult:
    if (reading := section.readings.get(item)) is None:
        return

    yield from check_temperature(
        reading=reading,
        params=params,
        unique_name=item,
        value_store=get_value_store(),
        dev_levels=section.upper_device_levels,
        dev_levels_lower=section.lower_device_levels,
    )


check_plugin_liebert_temp_fluid = CheckPlugin(
    name="liebert_temp_fluid",
    service_name="%s",
    discovery_function=discover_liebert_temp_fluid,
    check_function=check_liebert_temp_fluid,
    check_default_parameters={},
    check_ruleset_name="temperature",
)

#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Mapping

from .agent_based_api.v1 import register, SNMPTree
from .agent_based_api.v1.type_defs import StringTable
from .utils.liebert import DETECT_LIEBERT, parse_liebert, temperature_to_celsius


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
        lower_device_levels=(lower_warn, lower_crit)
        if lower_warn is not None and lower_crit is not None
        else None,
    )


register.snmp_section(
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

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Analog tables of the PowerNet-MIB `cooling` group

Newer APC cooling units (e.g. the InRow ACRC301S) do not populate the airIRRC objects
of the `airConditioners` group anymore. They publish generic description/value/units/scale
rows under coolingUnit (.1.3.6.1.4.1.318.1.1.27.1) instead:

.1.3.6.1.4.1.318.1.1.27.1.4.1.2.1.2.1.2 Supply Air Temperature --> coolingUnitStatusAnalogDescription
.1.3.6.1.4.1.318.1.1.27.1.4.1.2.1.3.1.2 159                    --> coolingUnitStatusAnalogValue
.1.3.6.1.4.1.318.1.1.27.1.4.1.2.1.4.1.2 C                      --> coolingUnitStatusAnalogUnits
.1.3.6.1.4.1.318.1.1.27.1.4.1.2.1.5.1.2 10                     --> coolingUnitStatusAnalogScale
"""

from collections.abc import Iterator
from dataclasses import dataclass

from cmk.agent_based.v2 import SNMPTree, StringTable

_ANALOG_ENTRY_COLUMNS = ["2", "3", "4", "5"]  # Description, Value, Units, Scale

COOLING_UNIT_STATUS_ANALOG = SNMPTree(
    base=".1.3.6.1.4.1.318.1.1.27.1.4.1.2.1",  # coolingUnitStatusAnalogEntry
    oids=_ANALOG_ENTRY_COLUMNS,
)

COOLING_UNIT_EXTENDED_ANALOG = SNMPTree(
    base=".1.3.6.1.4.1.318.1.1.27.1.6.1.2.1",  # coolingUnitExtendedAnalogEntry
    oids=_ANALOG_ENTRY_COLUMNS,
)


@dataclass(frozen=True)
class AnalogReading:
    description: str
    value: float
    units: str


def parse_analog_readings(string_table: StringTable) -> Iterator[AnalogReading]:
    for description, value, units, scale in string_table:
        try:
            yield AnalogReading(description, float(value) / float(scale), units)
        except (ValueError, ZeroDivisionError):
            # The value cell is missing for sensor slots that are not equipped,
            # e.g. "Rack Inlet Temperature 2" on a unit with one rack inlet sensor.
            continue

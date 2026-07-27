#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared PSU section model for the F5OS rSeries plugin family.

Both the PSU check and the hardware inventory consume the ``f5os_rseries_psu``
section, so its data type and parser live here.
"""

from dataclasses import dataclass

from cmk.agent_based.v2 import StringTable


@dataclass(frozen=True)
class F5OSPSU:
    name: str  # psuName (item key)
    serial: str  # psuSerial (inventory)
    model: str  # psuModel (inventory)
    current_in: float  # psuCurrentIn (A)
    current_out: float  # psuCurrentOut (A)
    voltage_in: float  # psuVoltageIn (V)
    voltage_out: float  # psuVoltageOut (V)
    temp1: float  # psuTemperature1 (°C)
    power_in: float  # psuPowerIn (W)
    power_out: float  # psuPowerOut (W)


def parse_f5os_rseries_psu(string_table: StringTable) -> dict[str, F5OSPSU] | None:
    if not string_table:
        return None
    result: dict[str, F5OSPSU] = {}
    for row in string_table:
        name = row[0].strip("\0")
        if not name:
            continue
        result[name] = F5OSPSU(
            name=name,
            serial=row[1].strip("\0"),
            model=row[2].strip("\0"),
            current_in=float(row[3]) / 1000.0,  # psuCurrentIn (unit: 0.001 A)
            current_out=float(row[4]) / 1000.0,  # psuCurrentOut (unit: 0.001 A)
            voltage_in=float(row[5]) / 1000.0,  # psuVoltageIn (unit: 0.001 V)
            voltage_out=float(row[6]) / 1000.0,  # psuVoltageOut (unit: 0.001 V)
            temp1=float(row[7]) / 10.0,  # psuTemperature1 (unit: 0.1°C)
            power_in=float(row[8]) / 1000.0,  # psuPowerIn (unit: 0.001 W)
            power_out=float(row[9]) / 1000.0,  # psuPowerOut (unit: 0.001 W)
        )
    return result

#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, SNMPTree

from cmk.plugins.lib.ibm import DETECT_IBM_IMM

from .agent_based_api.v1.type_defs import StringTable


@dataclass(frozen=True, kw_only=True)
class SensorTemperature:
    temperature: float
    upper_device_levels: tuple[float, float] | None
    lower_device_levels: tuple[float, float] | None


def parse_ibm_imm_temp(string_table: StringTable) -> dict[str, SensorTemperature]:
    temperature: dict[str, SensorTemperature] = {}
    for item, temp, dev_crit, dev_warn, dev_crit_lower, dev_warn_lower in string_table:
        try:
            reading = float(temp)
        except ValueError:
            continue

        try:
            dev_levels = float(dev_warn), float(dev_crit)
        except ValueError:
            dev_levels = None

        try:
            dev_levels_lower = float(dev_warn_lower), float(dev_crit_lower)
        except ValueError:
            dev_levels_lower = None

        temperature[item] = SensorTemperature(
            temperature=reading,
            upper_device_levels=dev_levels,
            lower_device_levels=dev_levels_lower,
        )

    return temperature


register.snmp_section(
    name="ibm_imm_temp",
    parse_function=parse_ibm_imm_temp,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.3.1.1.2.1",
        oids=["2", "3", "6", "7", "9", "10"],
    ),
    detect=DETECT_IBM_IMM,
)

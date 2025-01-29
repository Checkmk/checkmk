#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any

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
from cmk.plugins.lib.ibm import DETECT_IBM_IMM
from cmk.plugins.lib.temperature import check_temperature
from cmk.plugins.lib.temperature import TempParamType as TempParamType


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


snmp_section_ibm_imm_temp = SimpleSNMPSection(
    name="ibm_imm_temp",
    parse_function=parse_ibm_imm_temp,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.3.1.1.2.1",
        oids=["2", "3", "6", "7", "9", "10"],
    ),
    detect=DETECT_IBM_IMM,
)


def discover_ibm_imm_temp(section: Mapping[str, SensorTemperature]) -> DiscoveryResult:
    yield from (Service(item=name) for name in section if section[name].temperature != 0.0)


def _check_ibm_imm_temp(
    item: str,
    params: TempParamType,
    section: Mapping[str, SensorTemperature],
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    if not (temperature := section.get(item)):
        return

    yield from check_temperature(
        reading=temperature.temperature,
        params=params,
        unique_name=item,
        value_store=value_store,
        dev_levels=temperature.upper_device_levels,
        dev_levels_lower=temperature.lower_device_levels,
    )


def check_ibm_imm_temp(
    item: str, params: TempParamType, section: Mapping[str, SensorTemperature]
) -> CheckResult:
    yield from _check_ibm_imm_temp(item, params, section, get_value_store())


check_plugin_ibm_imm_temp = CheckPlugin(
    name="ibm_imm_temp",
    service_name="Temperature %s",
    discovery_function=discover_ibm_imm_temp,
    check_function=check_ibm_imm_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Any, Literal, TypedDict

from cmk.agent_based.v1.render import percent
from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.apc import DETECT_ATS


class ATS(TypedDict, total=False):
    voltage: float
    current: float
    perc_load: float
    power: float


Section = dict[str, ATS]


class DefaultParameters(TypedDict):
    output_voltage_max: LevelsT[float]
    output_voltage_min: LevelsT[float]
    output_current_max: LevelsT[float]
    output_current_min: LevelsT[float]
    output_power_max: LevelsT[float]
    output_power_min: LevelsT[float]
    load_perc_max: LevelsT[float]
    load_perc_min: LevelsT[float]


def parse_apc_ats_output(string_table: StringTable) -> Section:
    parsed: Section = {}

    # Define a mapping of keys to their respective factors
    conversion_factors: dict[Literal["voltage", "current", "perc_load", "power"], float] = {
        "voltage": 1.0,
        "current": 0.1,
        "perc_load": 1.0,
        "power": 1.0,
    }

    for index, voltage_str, current_str, perc_load_str, power_str in string_table:
        for key, value_str in zip(
            conversion_factors.keys(),
            [voltage_str, current_str, perc_load_str, power_str],
        ):
            factor: float = conversion_factors[key]
            try:
                value: float = float(value_str) * factor
            except ValueError:
                continue
            instance = parsed.setdefault(index, {})
            instance[key] = value
    return parsed


def discover_apc_ats_output(section: Any) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_apc_ats_output(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return

    if (voltage := data.get("voltage")) is not None:
        yield from check_levels(
            value=voltage,
            metric_name="volt",
            levels_upper=params.get("output_voltage_max", None),
            levels_lower=params.get("output_voltage_min", None),
            label="Voltage",
            render_func=lambda v: f"{v:.2f} V",
        )
    if (power := data.get("power")) is not None:
        yield from check_levels(
            value=power,
            metric_name="watt",
            levels_upper=params.get("output_power_max", None),
            levels_lower=params.get("output_power_min", None),
            label="Power",
            render_func=lambda v: f"{v:.2f} W",
        )

    if (current := data.get("current")) is not None:
        yield from check_levels(
            value=current,
            metric_name="current",
            levels_upper=params.get("output_current_max", None),
            levels_lower=params.get("output_current_min", None),
            label="Current",
            render_func=lambda v: f"{v:.2f} A",
        )

    if (perc_load := data.get("perc_load")) is not None:
        # -1 means that the ATS doesn't support this value
        if perc_load != -1:
            yield from check_levels(
                value=perc_load,
                metric_name="load_perc",
                levels_lower=params.get("load_perc_min", None),
                levels_upper=params.get("load_perc_max", None),
                label="Load",
                render_func=percent,
            )


snmp_section_apc_ats_output = SimpleSNMPSection(
    name="apc_ats_output",
    detect=DETECT_ATS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.8.5.4.3.1",
        oids=["1", "3", "4", "10", "13"],
    ),
    parse_function=parse_apc_ats_output,
)

check_plugin_apc_ats_output = CheckPlugin(
    name="apc_ats_output",
    service_name="Phase %s output",
    discovery_function=discover_apc_ats_output,
    check_function=check_apc_ats_output,
    check_ruleset_name="apc_ats_output",
    check_default_parameters=DefaultParameters(
        output_voltage_max=("fixed", (240, 250)),
        output_voltage_min=("no_levels", None),
        output_current_max=("no_levels", None),
        output_current_min=("no_levels", None),
        output_power_max=("no_levels", None),
        output_power_min=("no_levels", None),
        load_perc_min=("no_levels", None),
        load_perc_max=("fixed", (85.0, 95.0)),
    ),
)

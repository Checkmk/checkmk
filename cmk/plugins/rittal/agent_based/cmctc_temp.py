#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import NamedTuple

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.rittal.lib.cmctc import (
    cmctc_translate_status,
    cmctc_translate_status_text,
    DETECT_CMCTC,
)

# Table columns:
# 0: index
# 1: sensor type (10 = temperature)
# 2: sensor state (4 = ok)
# 3: current value (temperature)
# 4: critical level
# 5: warn low level
# 6: warn level
# 7: description


class Sensor(NamedTuple):
    status: int
    reading: int
    levels: tuple[float, float]
    levels_lower: tuple[float, float]


Section = Mapping[str, Sensor]


_TABLES = ["3", "4", "5", "6"]


def parse_cmctc_temp(string_table: Sequence[StringTable]) -> Section | None:
    return {
        f"{table}.{item}": Sensor(
            status=int(status),
            reading=int(reading),
            levels=(float(warn), float(crit)),
            levels_lower=(float(low), float("-inf")),
        )
        for table, block in zip(_TABLES, string_table)
        for item, type_, status, reading, crit, low, warn in block
        if type_ and int(type_) == 10
    }


def discover_cmctc_temp(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_cmctc_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    yield from check_temperature(
        sensor.reading,
        params,
        unique_name=f"cmctc_temp_{item}",
        value_store=get_value_store(),
        dev_levels=sensor.levels,
        dev_levels_lower=sensor.levels_lower,
        dev_status=cmctc_translate_status(sensor.status),
        dev_status_name=f"Unit: {cmctc_translate_status_text(sensor.status)}",
    )


snmp_section_cmctc_temp = SNMPSection(
    name="cmctc_temp",
    detect=DETECT_CMCTC,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2606.4.2.3.5.2.1",
            oids=["1", "2", "4", "5", "6", "7", "8"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2606.4.2.4.5.2.1",
            oids=["1", "2", "4", "5", "6", "7", "8"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2606.4.2.5.5.2.1",
            oids=["1", "2", "4", "5", "6", "7", "8"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2606.4.2.6.5.2.1",
            oids=["1", "2", "4", "5", "6", "7", "8"],
        ),
    ],
    parse_function=parse_cmctc_temp,
)


check_plugin_cmctc_temp = CheckPlugin(
    name="cmctc_temp",
    service_name="Temperature %s",
    discovery_function=discover_cmctc_temp,
    check_function=check_cmctc_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)

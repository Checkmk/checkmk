#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

from collections.abc import Iterable, Mapping
from typing import NamedTuple

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature, TempParamType
from cmk.plugins.cmctc.lib import cmctc_translate_status, cmctc_translate_status_text, DETECT_CMCTC

check_info = {}

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


def parse_cmctc_temp(string_table: list[StringTable]) -> Section:
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


def discover_cmctc_temp(section: Section) -> Iterable[tuple[str, dict]]:
    yield from ((item, {}) for item in section)


def check_cmctc_temp(item: str, params: TempParamType, section: Section) -> Iterable:
    if (sensor := section.get(item)) is None:
        return

    yield check_temperature(
        sensor.reading,
        params,
        "cmctc_temp_%s" % item,
        dev_levels=sensor.levels,
        dev_levels_lower=sensor.levels_lower,
        dev_status=cmctc_translate_status(sensor.status),
        dev_status_name="Unit: %s" % cmctc_translate_status_text(sensor.status),
    )


check_info["cmctc_temp"] = LegacyCheckDefinition(
    name="cmctc_temp",
    detect=DETECT_CMCTC,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2606.4.2.3",
            oids=[
                "5.2.1.1",
                "5.2.1.2",
                "5.2.1.4",
                "5.2.1.5",
                "5.2.1.6",
                "5.2.1.7",
                "5.2.1.8",
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2606.4.2.4",
            oids=[
                "5.2.1.1",
                "5.2.1.2",
                "5.2.1.4",
                "5.2.1.5",
                "5.2.1.6",
                "5.2.1.7",
                "5.2.1.8",
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2606.4.2.5",
            oids=[
                "5.2.1.1",
                "5.2.1.2",
                "5.2.1.4",
                "5.2.1.5",
                "5.2.1.6",
                "5.2.1.7",
                "5.2.1.8",
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2606.4.2.6",
            oids=[
                "5.2.1.1",
                "5.2.1.2",
                "5.2.1.4",
                "5.2.1.5",
                "5.2.1.6",
                "5.2.1.7",
                "5.2.1.8",
            ],
        ),
    ],
    parse_function=parse_cmctc_temp,
    service_name="Temperature %s",
    discovery_function=discover_cmctc_temp,
    check_function=check_cmctc_temp,
    check_ruleset_name="temperature",
)

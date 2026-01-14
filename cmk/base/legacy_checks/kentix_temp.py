#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Iterable, Mapping
from typing import Final, NamedTuple

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.kentix.lib import DETECT_KENTIX
from cmk.plugins.lib.temperature import TempParamType

check_info = {}

_TABLES: Final = {
    "2": "LAN",
    "3": "Rack",
}


class Sensor(NamedTuple):
    reading: float
    dev_levels: tuple[float, float]
    dev_levels_lower: tuple[float, float]


Section = Mapping[str, Sensor]


def parse_kentix_temp(string_table: list[StringTable]) -> Section:
    return {
        item: Sensor(
            reading=float(value) / 10,
            dev_levels=(float(upper_warn), float(upper_warn)),
            dev_levels_lower=(float(lower_warn), float(lower_warn)),
        )
        for item, block in zip(_TABLES.values(), string_table)
        for value, lower_warn, upper_warn in block
    }


def discover_kentix_temp(section: Section) -> Iterable[tuple[str, dict]]:
    yield from ((item, {}) for item in section)


def check_kentix_temp(
    item: str, params: TempParamType, section: Section
) -> Iterable[tuple[int, str, list]]:
    if (sensor := section.get(item)) is None:
        return

    yield check_temperature(
        sensor.reading,
        params,
        "kentix_temp_%s" % item,
        dev_levels=sensor.dev_levels,
        dev_levels_lower=sensor.dev_levels_lower,
    )


check_info["kentix_temp"] = LegacyCheckDefinition(
    name="kentix_temp",
    detect=DETECT_KENTIX,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.37954.2.1.1",
            oids=["1", "2", "3"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.37954.3.1.1",
            oids=["1", "2", "3"],
        ),
    ],
    parse_function=parse_kentix_temp,
    service_name="Temperature %s",
    discovery_function=discover_kentix_temp,
    check_function=check_kentix_temp,
    check_ruleset_name="temperature",
)

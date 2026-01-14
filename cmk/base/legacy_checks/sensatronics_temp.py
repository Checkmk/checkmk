#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Iterable, Mapping

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, equals, SNMPTree
from cmk.base.check_legacy_includes.temperature import check_temperature, TempParamType

check_info = {}

Section = Mapping[str, float]


_TABLES = list(range(16))


def parse_sensatronics_temp(string_table: list[list[list[str]]]) -> Section:
    parsed = {}
    for oid, block in zip(_TABLES, string_table):
        for name, reading in block:
            try:
                parsed[f"{oid}.{name}"] = float(reading)
            except ValueError:
                pass
    return parsed


def discover_sensatronics_temp(section: Section) -> Iterable[tuple[str, dict]]:
    yield from ((item, {}) for item in section)


def check_sensatronics_temp(
    item: str, params: TempParamType, section: Section
) -> Iterable[tuple[int, str, list]]:
    if (reading := section.get(item)) is None:
        return
    yield check_temperature(reading, params, "sensatronics_temp_%s" % item)


check_info["sensatronics_temp"] = LegacyCheckDefinition(
    name="sensatronics_temp",
    detect=any_of(equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.16174.1.1.1")),
    fetch=[
        SNMPTree(
            base=f".1.3.6.1.4.1.16174.1.1.1.3.{table}",
            oids=[
                "1.0",  # Sensor Name
                "2.0",  # Sensor Value
            ],
        )
        for table in _TABLES
    ],
    parse_function=parse_sensatronics_temp,
    service_name="Temperature %s",
    discovery_function=discover_sensatronics_temp,
    check_function=check_sensatronics_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (23.0, 25.0)},
)

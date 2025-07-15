#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping
from itertools import chain

from cmk.base.check_legacy_includes.humidity import check_humidity

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import (
    any_of,
    DiscoveryResult,
    OIDEnd,
    Service,
    SNMPTree,
    startswith,
    StringTable,
)

check_info = {}

# 19:1100, 38:822X
# .1.3.6.1.4.1.28507.**.1.6.1.1.3.1 498 --> GUDEADS-EPC****-MIB::epc****HygroSensor.1


Section = Mapping[str, float]


def parse_gude_humidity(string_table: list[StringTable]) -> Section:
    return {
        f"Sensor {index}": float(reading) / 10
        for index, reading in chain.from_iterable(string_table)
    }


def discover_gude_humidity(section: Section) -> DiscoveryResult:
    yield from (Service(item=name) for name, reading in section.items() if reading != -999.9)


def check_gude_humidity(
    item: str, params: tuple, section: Section
) -> Iterable[tuple[int, str, list]]:
    if (reading := section.get(item)) is None:
        return
    yield check_humidity(reading, params)


check_info["gude_humidity"] = LegacyCheckDefinition(
    name="gude_humidity",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.28507.19"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.28507.38"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.28507.66"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.28507.67"),
    ),
    fetch=[
        SNMPTree(
            base=f".1.3.6.1.4.1.28507.{table}.1.6.1.1",
            oids=[OIDEnd(), "3"],
        )
        for table in ["19", "38", "66", "67"]
    ],
    parse_function=parse_gude_humidity,
    service_name="Humidity %s",
    discovery_function=discover_gude_humidity,
    check_function=check_gude_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={
        "levels_lower": (0.0, 0.0),
        "levels": (60.0, 70.0),
    },
)

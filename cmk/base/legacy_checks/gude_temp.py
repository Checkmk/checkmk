#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Iterable, Mapping
from itertools import chain

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, OIDEnd, SNMPTree, startswith, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature, TempParamType

check_info = {}

# 19:1100, 38:822X
# .1.3.6.1.4.1.28507.**.1.6.1.1.2.1 225 --> GUDEADS-EPC****-MIB::epc****TempSensor.1

# Similar default levels in other checks
Section = Mapping[str, float]


def parse_gude_temp(string_table: list[StringTable]) -> Section:
    return {
        f"Sensor {index}": float(reading) / 10
        for index, reading in chain.from_iterable(string_table)
    }


def discover_gude_temp(section: Section) -> Iterable[tuple[str, dict]]:
    yield from ((name, {}) for name, reading in section.items() if reading != -999.9)


def check_gude_temp(
    item: str, params: TempParamType, section: Section
) -> Iterable[tuple[int, str, list]]:
    if (reading := section.get(item)) is None:
        return
    yield check_temperature(reading, params, "gude_temp.%s" % item)


check_info["gude_temp"] = LegacyCheckDefinition(
    name="gude_temp",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.28507.19"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.28507.38"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.28507.66"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.28507.67"),
    ),
    fetch=[
        SNMPTree(
            base=f".1.3.6.1.4.1.28507.{table}.1.6.1.1",
            oids=[OIDEnd(), "2"],
        )
        for table in ["19", "38", "66", "67"]
    ],
    parse_function=parse_gude_temp,
    service_name="Temperature %s",
    discovery_function=discover_gude_temp,
    check_function=check_gude_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (35.0, 40.0),
    },
)

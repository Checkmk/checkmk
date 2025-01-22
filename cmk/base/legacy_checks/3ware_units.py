#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<3ware_units>>>
# u0    RAID-5    OK             -       -       64K     1788.08   ON     OFF
# u1    RAID-5    INOPERABLE     -       -       64K     1788.08   OFF    OFF

# Different versions of tw_cli have different outputs. This means the size column
# used by this check is in different places. Here is a an example:
#
# Unit  UnitType  Status         %Cmpl  Stripe  Size(GB)  Cache  AVerify IgnECC
# u0    RAID-5    INITIALIZING   84     64K     1396.95   ON     ON      OFF
#
# Unit  UnitType  Status         %RCmpl  %V/I/M  Stripe  Size(GB)  Cache  AVrfy
# u0    RAID-5    OK             -       -       64K     1396.95   ON     ON


from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.legacy.v0_unstable import (
    LegacyCheckDefinition,
    LegacyCheckResult,
    LegacyDiscoveryResult,
)
from cmk.agent_based.v2 import StringTable

check_info = {}


@dataclass(frozen=True)
class Unit:
    type: str
    status: str
    complete: str
    size: float


Section = Mapping[str, Unit]


def parse_3ware_units(string_table: StringTable) -> Section:
    def _find_size_column(line: Sequence[str]) -> float:
        # Handle different outputs of tw_cli
        try:
            return float(line[2])
        except ValueError:
            return float(line[1])

    return {
        name: Unit(
            type=unit_type,
            status=status,
            complete=complete,
            size=_find_size_column(rest),
        )
        for name, unit_type, status, complete, *rest in string_table
    }


def discover_3ware_units(section: Section) -> LegacyDiscoveryResult:
    yield from ((name, {}) for name in section)


def check_3ware_units(item: str, _no_params: object, section: Section) -> LegacyCheckResult:
    if (unit := section.get(item)) is None:
        return

    match unit.status:
        case "OK" | "VERIFYING":
            state = 0
        case "INITIALIZING" | "VERIFY-PAUSED" | "REBUILDING":
            state = 1
        case _:
            state = 2

    yield state, unit.status
    yield 0, f"Type: {unit.type}"
    yield 0, f"Size: {unit.size}GB"
    if unit.complete != "-":
        yield 0, f"Complete: {unit.complete}%"


check_info["3ware_units"] = LegacyCheckDefinition(
    name="3ware_units",
    parse_function=parse_3ware_units,
    service_name="RAID 3ware unit %s",
    discovery_function=discover_3ware_units,
    check_function=check_3ware_units,
    check_ruleset_name="raid",
)

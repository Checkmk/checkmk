#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


from collections.abc import Iterable, Mapping
from typing import Literal, TypedDict

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.plugins.ups.lib import DETECT_UPS_CPS

check_info = {}


class Phase(TypedDict):
    voltage: float
    frequency: float
    output_load: float
    current: float


Section = Mapping[Literal["1"], Phase]


def parse_ups_cps_outphase(string_table: list[str]) -> Section | None:
    return (
        {
            "1": Phase(
                voltage=float(string_table[0][0]) / 10,
                frequency=float(string_table[0][1]) / 10,
                output_load=float(string_table[0][2]),
                current=float(string_table[0][3]) / 10,
            )
        }
        if string_table
        else None
    )


def discover_ups_cps_outphase(section: Section) -> Iterable[tuple[str, dict]]:
    yield "1", {}


check_info["ups_cps_outphase"] = LegacyCheckDefinition(
    name="ups_cps_outphase",
    detect=DETECT_UPS_CPS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3808.1.1.1.4.2",
        oids=["1", "2", "3", "4"],
    ),
    parse_function=parse_ups_cps_outphase,
    service_name="UPS Output Phase %s",
    discovery_function=discover_ups_cps_outphase,
    check_function=check_elphase,
    check_ruleset_name="ups_outphase",
)

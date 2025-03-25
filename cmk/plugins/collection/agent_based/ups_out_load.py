#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    render,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.ups import DETECT_UPS_GENERIC


class UpsPowerVoltage(NamedTuple):
    power: int
    voltage: int


Section = dict[str, UpsPowerVoltage]


def int_or_zero(value: str) -> int:
    if value == "":
        return 0
    return int(value)


def parse_ups_load(string_table: Sequence[StringTable]) -> Section:
    return {i: UpsPowerVoltage(int_or_zero(p), int_or_zero(v)) for v, p, i in string_table[0]}


snmp_section_ups_out_load = SNMPSection(
    name="ups_out_load",
    detect=DETECT_UPS_GENERIC,
    parse_function=parse_ups_load,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.33.1.4.4.1",
            oids=[
                "2",
                "5",
                OIDEnd(),
            ],
        ),
    ],
)


def discovery_ups(section: Section) -> DiscoveryResult:
    for key, ups in section.items():
        if ups.voltage:
            yield Service(item=key)


def check_ups_out_load(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    ups = section.get(item)
    if ups is None:
        yield Result(state=State.UNKNOWN, summary=f"Phase {item} not found in SNMP output")
        return

    yield from check_levels_v1(
        value=ups.power,
        levels_upper=params["levels"],
        metric_name="out_load",
        render_func=render.percent,
        label="load",
    )


check_plugin_ups_out_load = CheckPlugin(
    name="ups_out_load",
    service_name="OUT load phase %s",
    discovery_function=discovery_ups,
    check_function=check_ups_out_load,
    check_default_parameters={"levels": (85, 90)},
    check_ruleset_name="ups_out_load",
)

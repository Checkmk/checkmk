#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List, Mapping, NamedTuple

from .agent_based_api.v1 import (
    check_levels,
    OIDEnd,
    register,
    render,
    Result,
    Service,
    SNMPTree,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.ups import DETECT_UPS_GENERIC


class UpsPowerVoltage(NamedTuple):
    power: int
    voltage: int


Section = Dict[str, UpsPowerVoltage]


def int_or_zero(value: str) -> int:
    if value == "":
        return 0
    return int(value)


def parse_ups_load(string_table: List[StringTable]) -> Section:
    return {i: UpsPowerVoltage(int_or_zero(p), int_or_zero(v)) for v, p, i in string_table[0]}


register.snmp_section(
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

    yield from check_levels(
        value=ups.power,
        levels_upper=params["levels"],
        metric_name="out_load",
        render_func=render.percent,
        label="load",
    )


register.check_plugin(
    name="ups_out_load",
    service_name="OUT load phase %s",
    discovery_function=discovery_ups,
    check_function=check_ups_out_load,
    check_default_parameters={"levels": (85, 90)},
    check_ruleset_name="ups_out_load",
)

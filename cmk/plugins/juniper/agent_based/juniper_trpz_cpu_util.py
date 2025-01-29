#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.juniper import DETECT_JUNIPER_TRPZ


class Params(TypedDict):
    util: tuple[float, float]


class Section(NamedTuple):
    utilc: int
    util1: int
    util5: int


def saveint(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


def discovery_juniper_trpz_cpu_util(section: Section) -> DiscoveryResult:
    yield Service()


def check_juniper_trpz_cpu_util(params: Params, section: Section) -> CheckResult:
    yield from check_levels_v1(
        value=section.utilc,
        metric_name="utilc",
        render_func=lambda v: f"{v}% current",
    )
    yield from check_levels_v1(
        value=section.util1,
        levels_upper=params["util"],
        metric_name="util1",
        render_func=lambda v: f"{v}% 1min",
    )
    yield from check_levels_v1(
        value=section.util5,
        levels_upper=params["util"],
        metric_name="util5",
        render_func=lambda v: f"{v}% 5min",
    )


def parse_juniper_trpz_cpu_util(string_table: StringTable) -> Section | None:
    if not string_table:
        return None
    utilc, util1, util5 = map(saveint, string_table[0])
    return Section(utilc=utilc, util1=util1, util5=util5)


snmp_section_juniper_trpz_cpu_util = SimpleSNMPSection(
    name="juniper_trpz_cpu_util",
    detect=DETECT_JUNIPER_TRPZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14525.4.8.1.1.11",
        oids=["1", "2", "3"],
    ),
    parse_function=parse_juniper_trpz_cpu_util,
)

check_plugin_juniper_trpz_cpu_util = CheckPlugin(
    name="juniper_trpz_cpu_util",
    service_name="CPU utilization",
    discovery_function=discovery_juniper_trpz_cpu_util,
    check_function=check_juniper_trpz_cpu_util,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)

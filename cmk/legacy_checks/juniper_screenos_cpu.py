#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import NamedTuple

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.juniper.lib import DETECT_JUNIPER_SCREENOS


class Section(NamedTuple):
    util1: float
    util15: float


def _migrate_levels(levels: object) -> LevelsT[float] | None:
    # Legacy rules stored bare tuples (warn, crit); v2 API requires tagged tuples.
    if isinstance(levels, tuple) and len(levels) == 2 and isinstance(levels[0], float):
        return ("fixed", levels)
    return levels  # type: ignore[return-value]


def discover_juniper_screenos_cpu(section: Section) -> DiscoveryResult:
    yield Service()


def check_juniper_screenos_cpu(params: Mapping[str, object], section: Section) -> CheckResult:
    yield from check_levels(
        section.util1,
        metric_name="util1",
        render_func=render.percent,
        label="1min",
    )
    yield from check_levels(
        section.util15,
        levels_upper=_migrate_levels(params.get("util")),
        metric_name="util15",
        render_func=render.percent,
        label="15min",
    )


def parse_juniper_screenos_cpu(string_table: StringTable) -> Section | None:
    if not string_table:
        return None
    util1, util15 = map(float, string_table[0])
    return Section(util1=util1, util15=util15)


snmp_section_juniper_screenos_cpu = SimpleSNMPSection(
    name="juniper_screenos_cpu",
    detect=DETECT_JUNIPER_SCREENOS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3224.16.1",
        oids=["2", "4"],
    ),
    parse_function=parse_juniper_screenos_cpu,
)

check_plugin_juniper_screenos_cpu = CheckPlugin(
    name="juniper_screenos_cpu",
    service_name="CPU utilization",
    discovery_function=discover_juniper_screenos_cpu,
    check_function=check_juniper_screenos_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)

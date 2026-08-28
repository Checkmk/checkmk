#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    exists,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

Section = int


def parse_fortigate_memory(string_table: StringTable) -> Section | None:
    try:
        return int(string_table[0][0])
    except ValueError, IndexError:
        return None


def discover_fortigate_memory(section: Section) -> DiscoveryResult:
    yield Service()


def check_fortigate_memory(params: Mapping[str, Any], section: Section) -> CheckResult:
    warn, crit = params["levels"]
    if isinstance(warn, int):
        yield Result(state=State.UNKNOWN, summary="Absolute levels are not supported")
        levels_upper = None
    elif warn < 0:
        # The checkgroup "memory" might set negative values which act as levels for free space
        # These levels are converted to used space, too..
        levels_upper = (100 + warn, 100 + crit)
    else:
        levels_upper = (warn, crit)

    yield from check_levels_v1(
        section,
        metric_name="mem_usage",
        levels_upper=levels_upper,
        render_func=render.percent,
        label="Usage",
    )


snmp_section_fortigate_memory = SimpleSNMPSection(
    name="fortigate_memory",
    detect=all_of(contains(".1.3.6.1.2.1.1.1.0", "fortigate"), exists(".1.3.6.1.4.1.12356.1.9.0")),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.1",
        oids=["9"],
    ),
    parse_function=parse_fortigate_memory,
)


check_plugin_fortigate_memory = CheckPlugin(
    name="fortigate_memory",
    service_name="Memory",
    discovery_function=discover_fortigate_memory,
    check_function=check_fortigate_memory,
    check_ruleset_name="memory",
    check_default_parameters={"levels": (70.0, 80.0)},
)

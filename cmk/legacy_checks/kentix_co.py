#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
# 2017 comNET GmbH, Bjoern Mueller

# Default levels from http://www.detectcarbonmonoxide.com/co-health-risks/

from collections.abc import Mapping
from typing import Any

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
from cmk.plugins.kentix.lib import DETECT_KENTIX


def parse_kentix_co(string_table: StringTable) -> int | None:
    if not string_table:
        return None
    for value in string_table[0]:
        try:
            return int(value)
        except ValueError:
            pass
    return None


def discover_kentix_co(section: int) -> DiscoveryResult:
    yield Service()


def check_kentix_co(params: Mapping[str, Any], section: int) -> CheckResult:
    yield from check_levels_v1(
        section,
        metric_name="parts_per_million",
        levels_upper=params["levels_ppm"],
        render_func=lambda x: f"{x} ppm",
        label="CO concentration",
    )


snmp_section_kentix_co = SimpleSNMPSection(
    name="kentix_co",
    detect=DETECT_KENTIX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.37954",
        oids=["2.1.4.1", "3.1.3.1"],
    ),
    parse_function=parse_kentix_co,
)


check_plugin_kentix_co = CheckPlugin(
    name="kentix_co",
    service_name="Carbon Monoxide",
    discovery_function=discover_kentix_co,
    check_function=check_kentix_co,
    check_ruleset_name="carbon_monoxide",
    check_default_parameters={
        "levels_ppm": (10, 25),
    },
)

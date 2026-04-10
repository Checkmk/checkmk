#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from cmk.plugins.tplink.lib import DETECT_TPLINK


def parse_tplink_poe_summary(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_tplink_poe_summary = SimpleSNMPSection(
    name="tplink_poe_summary",
    detect=DETECT_TPLINK,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11863.6.56.1.1.1",
        oids=["3"],
    ),
    parse_function=parse_tplink_poe_summary,
)


def discover_tplink_poe_summary(section: StringTable) -> DiscoveryResult:
    if section and section[0][0] != "0":
        yield Service()


def check_tplink_poe_summary(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    if not section:
        return

    watt = float(section[0][0]) / 10
    yield from check_levels_v1(
        watt,
        metric_name="power",
        levels_upper=params.get("levels"),
        render_func=lambda x: f"{x:.2f} W",
    )


check_plugin_tplink_poe_summary = CheckPlugin(
    name="tplink_poe_summary",
    service_name="POE Power",
    discovery_function=discover_tplink_poe_summary,
    check_function=check_tplink_poe_summary,
    check_ruleset_name="epower_single",
    check_default_parameters={"levels": None},
)

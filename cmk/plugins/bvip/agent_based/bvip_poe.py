#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.bvip.lib import DETECT_BVIP


def parse_bvip_poe(string_table: StringTable) -> StringTable:
    return string_table


def discover_bvip_poe(section: StringTable) -> DiscoveryResult:
    if section and section[0][0] != "0":
        yield Service()


def check_bvip_poe(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    watt = float(section[0][0]) / 10
    yield from check_levels(
        watt,
        levels_upper=("no_levels", None) if (l := params["levels"]) is None else ("fixed", l),
        metric_name="power",
        render_func=lambda x: f"{x:.2f} W",
    )


snmp_section_bvip_poe = SimpleSNMPSection(
    name="bvip_poe",
    detect=DETECT_BVIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3967.1.1",
        oids=["10"],
    ),
    parse_function=parse_bvip_poe,
)


check_plugin_bvip_poe = CheckPlugin(
    name="bvip_poe",
    service_name="POE Power",
    discovery_function=discover_bvip_poe,
    check_function=check_bvip_poe,
    check_ruleset_name="epower_single",
    check_default_parameters={"levels": (50, 60)},
)

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.bvip.lib import DETECT_BVIP

check_info = {}


def discover_bvip_poe(info):
    if not info:
        return []
    if info[0][0] != "0":
        return [(None, {})]
    return []


def check_bvip_poe(_no_item, params, info):
    watt = float(info[0][0]) / 10
    return check_levels(
        watt, "power", params.get("levels"), human_readable_func=lambda x: f"{x:.2f} W"
    )


def parse_bvip_poe(string_table: StringTable) -> StringTable:
    return string_table


check_info["bvip_poe"] = LegacyCheckDefinition(
    name="bvip_poe",
    parse_function=parse_bvip_poe,
    detect=DETECT_BVIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3967.1.1",
        oids=["10"],
    ),
    service_name="POE Power",
    discovery_function=discover_bvip_poe,
    check_function=check_bvip_poe,
    check_ruleset_name="epower_single",
    check_default_parameters={"levels": (50, 60)},
)

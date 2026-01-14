#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.tplink.lib import DETECT_TPLINK

check_info = {}


def discover_tplink_poe_summary(info):
    if info and info[0][0] != "0":
        return [(None, {})]
    return []


def check_tplink_poe_summary(_no_item, params, info):
    deci_watt = float(info[0][0])
    watt = deci_watt / 10
    return check_levels(
        watt, "power", params.get("levels"), human_readable_func=lambda x: f"{x:.2f} W"
    )


def parse_tplink_poe_summary(string_table: StringTable) -> StringTable:
    return string_table


check_info["tplink_poe_summary"] = LegacyCheckDefinition(
    name="tplink_poe_summary",
    parse_function=parse_tplink_poe_summary,
    detect=DETECT_TPLINK,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11863.6.56.1.1.1",
        oids=["3"],
    ),
    service_name="POE Power",
    discovery_function=discover_tplink_poe_summary,
    check_function=check_tplink_poe_summary,
    check_ruleset_name="epower_single",
    check_default_parameters={"levels": None},
)

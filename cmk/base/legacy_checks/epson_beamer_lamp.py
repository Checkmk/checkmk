#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import contains, SNMPTree, StringTable

check_info = {}


def discover_epson_beamer_lamp(info):
    if info:
        yield None, {}


def check_epson_beamer_lamp(_no_item, params, info):
    lamp_time = int(info[0][0]) * 3600
    return check_levels(
        lamp_time,
        None,
        params["levels"],
        human_readable_func=lambda x: f"{x // 3600} h",
        infoname="Operation time",
    )


def parse_epson_beamer_lamp(string_table: StringTable) -> StringTable:
    return string_table


check_info["epson_beamer_lamp"] = LegacyCheckDefinition(
    name="epson_beamer_lamp",
    parse_function=parse_epson_beamer_lamp,
    detect=contains(".1.3.6.1.2.1.1.2.0", "1248"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1248.4.1.1.1.1",
        oids=["0"],
    ),
    service_name="Beamer Lamp",
    discovery_function=discover_epson_beamer_lamp,
    check_function=check_epson_beamer_lamp,
    check_ruleset_name="lamp_operation_time",
    check_default_parameters={
        "levels": (1000 * 3600, 1500 * 3600),
    },
)

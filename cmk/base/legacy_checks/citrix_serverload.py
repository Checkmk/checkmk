#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# <<<citrix_serverload>>>
# 100


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, StringTable

check_info = {}


def discover_citrix_serverload(info):
    yield None, {}


def check_citrix_serverload(_no_item, params, info):
    try:
        load = int(info[0][0])
    except (IndexError, ValueError):
        return

    if load == 20000:
        yield 1, "License error"
        load = 10000

    yield check_levels(
        load / 100.0,
        "citrix_load",
        params["levels"],
        human_readable_func=render.percent,
        infoname="Current Citrix Load",
    )


def parse_citrix_serverload(string_table: StringTable) -> StringTable:
    return string_table


check_info["citrix_serverload"] = LegacyCheckDefinition(
    name="citrix_serverload",
    parse_function=parse_citrix_serverload,
    service_name="Citrix Serverload",
    discovery_function=discover_citrix_serverload,
    check_function=check_citrix_serverload,
    check_ruleset_name="citrix_load",
    check_default_parameters={
        "levels": (85.0, 95.0),
    },
)

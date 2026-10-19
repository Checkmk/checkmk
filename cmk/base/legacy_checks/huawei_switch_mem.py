#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render
from cmk.plugins.huawei.lib import HUAWEI_ENTERPRISE, parse_huawei_physical_entity_values

check_info = {}


def parse_huawei_switch_mem(string_table):
    return parse_huawei_physical_entity_values(string_table)


def check_huawei_switch_mem(item, params, parsed):
    if not (item_data := parsed.get(item)):
        return
    try:
        mem = float(item_data.value)
    except TypeError:
        return

    yield check_levels(
        mem,
        "mem_used_percent",
        params.get("levels", (None, None)),
        infoname="Usage",
        human_readable_func=render.percent,
    )


def discover_huawei_switch_mem(section):
    yield from ((item, {}) for item in section)


check_info["huawei_switch_mem"] = LegacyCheckDefinition(
    name="huawei_switch_mem",
    detect=HUAWEI_ENTERPRISE.switch_detect,
    fetch=HUAWEI_ENTERPRISE.entity_state_trees("7"),
    parse_function=parse_huawei_switch_mem,
    service_name="Memory %s",
    discovery_function=discover_huawei_switch_mem,
    check_function=check_huawei_switch_mem,
    check_ruleset_name="memory_percentage_used_multiitem",
    check_default_parameters={
        "levels": (80.0, 90.0),
    },
)

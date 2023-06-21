#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.huawei_switch import parse_huawei_physical_entity_values
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, render, SNMPTree
from cmk.base.plugins.agent_based.utils.huawei import DETECT_HUAWEI_SWITCH


def parse_huawei_switch_mem(info):
    return parse_huawei_physical_entity_values(info)


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
    detect=DETECT_HUAWEI_SWITCH,
    parse_function=parse_huawei_switch_mem,
    discovery_function=discover_huawei_switch_mem,
    check_function=check_huawei_switch_mem,
    service_name="Memory %s",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[OIDEnd(), "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2011.5.25.31.1.1.1.1",
            oids=[OIDEnd(), "7"],
        ),
    ],
    check_ruleset_name="memory_percentage_used_multiitem",
    check_default_parameters={
        "levels": (80.0, 90.0),
    },
)

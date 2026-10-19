#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition

# mypy: disable-error-code="var-annotated"
from cmk.agent_based.v2 import OIDEnd, render, SNMPTree
from cmk.plugins.lib.huawei import HUAWEI_ENTERPRISE, parse_huawei_switch_fan

check_info = {}


def inventory_huawei_switch_fan(parsed):
    for item, item_data in parsed.items():
        if item_data.fan_present:
            yield (item, {})


def check_huawei_switch_fan(item, params, parsed):
    if not (item_data := parsed.get(item)):
        return
    levels = params.get("levels", (None, None)) + params.get("levels_lower", (None, None))
    yield check_levels(item_data.fan_speed, "fan_perc", levels, human_readable_func=render.percent)


check_info["huawei_switch_fan"] = LegacyCheckDefinition(
    name="huawei_switch_fan",
    detect=HUAWEI_ENTERPRISE.switch_detect,
    fetch=SNMPTree(
        base=HUAWEI_ENTERPRISE.subtree("5.25.31.1.1.10.1"),
        oids=[OIDEnd(), "5", "6"],
    ),
    parse_function=parse_huawei_switch_fan,
    service_name="Fan %s",
    discovery_function=inventory_huawei_switch_fan,
    check_function=check_huawei_switch_fan,
    check_ruleset_name="hw_fans_perc",
)

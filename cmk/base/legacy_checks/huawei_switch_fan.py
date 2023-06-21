#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import collections

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.huawei_switch import huawei_item_dict_from_entities
from cmk.base.config import check_info

# mypy: disable-error-code="var-annotated"
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, render, SNMPTree
from cmk.base.plugins.agent_based.utils.huawei import DETECT_HUAWEI_SWITCH

HuaweiFanData = collections.namedtuple(  # pylint: disable=collections-namedtuple-call
    "HuaweiFanData", "fan_present fan_speed"
)


def parse_huawei_switch_fan(info):
    entities_per_member = {}
    for line in info:
        member_number = line[0].partition(".")[0]
        fan_present = line[2] == "1"

        try:
            fan_speed = float(line[1])
        except TypeError:
            continue

        entities_per_member.setdefault(member_number, []).append(
            HuaweiFanData(fan_present=fan_present, fan_speed=fan_speed)
        )

    return huawei_item_dict_from_entities(entities_per_member)


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
    detect=DETECT_HUAWEI_SWITCH,
    parse_function=parse_huawei_switch_fan,
    discovery_function=inventory_huawei_switch_fan,
    check_function=check_huawei_switch_fan,
    service_name="Fan %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2011.5.25.31.1.1.10.1",
        oids=[OIDEnd(), "5", "6"],
    ),
    check_ruleset_name="hw_fans_perc",
)

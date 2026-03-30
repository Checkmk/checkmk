#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v1 import check_levels
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    render,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.huawei.lib import (
    DETECT_HUAWEI_SWITCH,
    huawei_item_dict_from_entities,
)


@dataclass(frozen=True)
class HuaweiFanData:
    fan_present: bool
    fan_speed: float


class HuaweiFanParams(TypedDict, total=False):
    levels: tuple[float, float]
    levels_lower: tuple[float, float]


type Section = Mapping[str, HuaweiFanData]


def parse_huawei_switch_fan(string_table: StringTable) -> Section:
    entities_per_member = dict[str, list[HuaweiFanData]]()
    for line in string_table:
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


def discover_huawei_switch_fan(section: Section) -> DiscoveryResult:
    for item, item_data in section.items():
        if item_data.fan_present:
            yield Service(item=item)


def check_huawei_switch_fan(item: str, params: HuaweiFanParams, section: Section) -> CheckResult:
    if not (item_data := section.get(item)):
        return

    yield from check_levels(
        item_data.fan_speed,
        levels_upper=params.get("levels"),
        levels_lower=params.get("levels_lower"),
        metric_name="fan_perc",
        render_func=render.percent,
    )


snmp_section_huawei_switch_fan = SimpleSNMPSection(
    name="huawei_switch_fan",
    detect=DETECT_HUAWEI_SWITCH,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2011.5.25.31.1.1.10.1",
        oids=[OIDEnd(), "5", "6"],
    ),
    parse_function=parse_huawei_switch_fan,
)


check_plugin_huawei_switch_fan = CheckPlugin(
    name="huawei_switch_fan",
    service_name="Fan %s",
    discovery_function=discover_huawei_switch_fan,
    check_function=check_huawei_switch_fan,
    check_ruleset_name="hw_fans_perc",
    check_default_parameters={},
)

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from typing import List

from cmk.base.check_legacy_includes.huawei_switch import (
    parse_huawei_physical_entity_values,
    Section,
)
from cmk.base.check_legacy_includes.temperature import check_temperature, TempParamType
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.utils.huawei import DETECT_HUAWEI_SWITCH

factory_settings["huawei_switch_temp_default_levels"] = {
    "levels": (80.0, 90.0),
}


def parse_huawei_switch_temp(string_table: List[StringTable]) -> Section:
    return parse_huawei_physical_entity_values(string_table)


def discover_huawei_switch_temp(section: Section) -> Iterable[tuple[str, dict]]:
    yield from ((item, {}) for item in section)


def check_huawei_switch_temp(
    item: str, params: TempParamType, section: Section
) -> Iterable[tuple[int, str, list]]:
    if (item_data := section.get(item)) is None or item_data.value is None:
        return
    try:
        temp = float(item_data.value)
    except TypeError:
        return
    yield check_temperature(temp, params, "huawei_switch_temp_%s" % item_data.stack_member)


check_info["huawei_switch_temp"] = {
    "detect": DETECT_HUAWEI_SWITCH,
    "parse_function": parse_huawei_switch_temp,
    "discovery_function": discover_huawei_switch_temp,
    "check_function": check_huawei_switch_temp,
    "service_name": "Temperature %s",
    "fetch": [
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[OIDEnd(), "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2011.5.25.31.1.1.1.1",
            oids=[OIDEnd(), "11"],
        ),
    ],
    "check_ruleset_name": "temperature",
    "default_levels_variable": "huawei_switch_temp_default_levels",
}

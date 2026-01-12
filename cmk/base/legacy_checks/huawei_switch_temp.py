#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.agent_based.legacy.v0_unstable import (
    LegacyCheckDefinition,
    LegacyCheckResult,
    LegacyDiscoveryResult,
)
from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature, TempParamType
from cmk.plugins.huawei.lib import (
    DETECT_HUAWEI_SWITCH,
    parse_huawei_physical_entity_values,
    Section,
)

check_info = {}


def parse_huawei_switch_temp(string_table: Sequence[StringTable]) -> Section:
    return parse_huawei_physical_entity_values(string_table)


def discover_huawei_switch_temp(section: Section) -> LegacyDiscoveryResult:
    yield from ((item, {}) for item in section)


def check_huawei_switch_temp(
    item: str, params: TempParamType, section: Section
) -> LegacyCheckResult:
    if (item_data := section.get(item)) is None or item_data.value is None:
        return
    try:
        temp = float(item_data.value)
    except TypeError:
        return
    yield check_temperature(temp, params, "huawei_switch_temp_%s" % item_data.stack_member)


check_info["huawei_switch_temp"] = LegacyCheckDefinition(
    name="huawei_switch_temp",
    detect=DETECT_HUAWEI_SWITCH,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[OIDEnd(), "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2011.5.25.31.1.1.1.1",
            oids=[OIDEnd(), "11"],
        ),
    ],
    parse_function=parse_huawei_switch_temp,
    service_name="Temperature %s",
    discovery_function=discover_huawei_switch_temp,
    check_function=check_huawei_switch_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (80.0, 90.0),
    },
)

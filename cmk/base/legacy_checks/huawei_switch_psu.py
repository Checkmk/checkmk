#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.plugins.lib.huawei import (
    HUAWEI_ENTERPRISE,
    parse_huawei_switch_psu,
    Section,
)

check_info = {}

huawei_switch_hw_oper_state_map = {
    "1": "notSupported",
    "2": "disabled",
    "3": "enabled",
    "4": "offline",
}


def discover_huawei_switch_psu(section: Section) -> Iterable[tuple[str, dict]]:
    yield from ((item, {}) for item in section)


def check_huawei_switch_psu(
    item: str, params: Mapping, section: Section
) -> Iterable[tuple[int, str]]:
    if (item_data := section.get(item)) is None or item_data.value is None:
        return

    # Only 'enabled' is OK, everything else is considered CRIT
    status = 0 if item_data.value == "3" else 2
    status_text = huawei_switch_hw_oper_state_map.get(
        item_data.value, "unknown (%s)" % item_data.value
    )
    yield status, "State: %s" % status_text


check_info["huawei_switch_psu"] = LegacyCheckDefinition(
    name="huawei_switch_psu",
    detect=HUAWEI_ENTERPRISE.switch_detect,
    fetch=HUAWEI_ENTERPRISE.entity_state_trees("2"),
    parse_function=parse_huawei_switch_psu,
    service_name="Powersupply %s",
    discovery_function=discover_huawei_switch_psu,
    check_function=check_huawei_switch_psu,
)

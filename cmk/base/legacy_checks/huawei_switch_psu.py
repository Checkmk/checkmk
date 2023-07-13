#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping
from typing import List

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.huawei_switch import (
    parse_huawei_physical_entity_values,
    Section,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.utils.huawei import DETECT_HUAWEI_SWITCH

huawei_switch_hw_oper_state_map = {
    "1": "notSupported",
    "2": "disabled",
    "3": "enabled",
    "4": "offline",
}


def parse_huawei_switch_psu(string_table: List[StringTable]) -> Section:
    return parse_huawei_physical_entity_values(string_table, "power card")


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
    detect=DETECT_HUAWEI_SWITCH,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[OIDEnd(), "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2011.5.25.31.1.1.1.1",
            oids=[OIDEnd(), "2"],
        ),
    ],
    parse_function=parse_huawei_switch_psu,
    service_name="Powersupply %s",
    discovery_function=discover_huawei_switch_psu,
    check_function=check_huawei_switch_psu,
)

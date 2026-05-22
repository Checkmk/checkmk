#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.emc.lib import DETECT_ISILON
from cmk.plugins.lib.fan import check_fan


# Examples for sensor names:
# Chassis Fan1 (ISI F1) --> Chassis 1
# Chassis Fan2 (ISI F2)
# Chassis Fan3 (ISI F3)
# Power Supply 1 Fan1 --> Power Supply 1 1
# Power Supply 2 Fan1
def _isilon_fan_item_name(sensor_name: str) -> str:
    return sensor_name.replace("Fan", "").split("(")[0].strip()


def parse_emc_isilon_fans(string_table: StringTable) -> StringTable:
    return string_table


def discover_emc_isilon_fans(section: StringTable) -> DiscoveryResult:
    for fan_name, _value in section:
        yield Service(item=_isilon_fan_item_name(fan_name))


def check_emc_isilon_fans(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    for fan_name, value in section:
        if item == _isilon_fan_item_name(fan_name):
            yield from check_fan(float(value), params)
            return


snmp_section_emc_isilon_fans = SimpleSNMPSection(
    name="emc_isilon_fans",
    parse_function=parse_emc_isilon_fans,
    detect=DETECT_ISILON,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12124.2.53.1",
        oids=["3", "4"],
    ),
)


check_plugin_emc_isilon_fans = CheckPlugin(
    name="emc_isilon_fans",
    service_name="Fan %s",
    discovery_function=discover_emc_isilon_fans,
    check_function=check_emc_isilon_fans,
    check_ruleset_name="hw_fans",
    check_default_parameters={"lower": (3000, 2500)},
)

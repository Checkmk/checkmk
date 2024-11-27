#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.fan import check_fan

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import DiscoveryResult, equals, Service, SNMPTree, StringTable

check_info = {}


def discover_climaveneta_fan(section: StringTable) -> DiscoveryResult:
    if section and len(section[0]) == 2:
        yield Service(item="1")
        yield Service(item="2")


def check_climaveneta_fan(item, params, info):
    rpm = int(info[0][int(item) - 1])
    return check_fan(rpm, params)


def parse_climaveneta_fan(string_table: StringTable) -> StringTable:
    return string_table


check_info["climaveneta_fan"] = LegacyCheckDefinition(
    name="climaveneta_fan",
    parse_function=parse_climaveneta_fan,
    detect=equals(".1.3.6.1.2.1.1.1.0", "pCO Gateway"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9839.2.1.2",
        oids=["42", "43"],
    ),
    service_name="Fan %s",
    discovery_function=discover_climaveneta_fan,
    check_function=check_climaveneta_fan,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (200, 100),
    },
)

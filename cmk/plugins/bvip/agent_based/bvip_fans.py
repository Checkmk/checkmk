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
    OIDEnd,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.bvip.lib import DETECT_BVIP
from cmk.plugins.lib.fan import check_fan


def parse_bvip_fans(string_table: StringTable) -> StringTable:
    return string_table


def discover_bvip_fans(section: StringTable) -> DiscoveryResult:
    for line in section:
        rpm = int(line[1])
        if rpm != 0:
            yield Service(item=line[0], parameters={"lower": (rpm * 0.9, rpm * 0.8)})


def check_bvip_fans(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    for nr, value in section:
        if nr == item:
            yield from check_fan(int(value), params)
            return


snmp_section_bvip_fans = SimpleSNMPSection(
    name="bvip_fans",
    detect=DETECT_BVIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3967.1.1.8.1",
        oids=[OIDEnd(), "1"],
    ),
    parse_function=parse_bvip_fans,
)


check_plugin_bvip_fans = CheckPlugin(
    name="bvip_fans",
    service_name="Fan %s",
    discovery_function=discover_bvip_fans,
    check_function=check_bvip_fans,
    check_ruleset_name="hw_fans",
    check_default_parameters={},
)

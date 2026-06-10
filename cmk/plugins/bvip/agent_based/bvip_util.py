#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.bvip.lib import DETECT_BVIP
from cmk.plugins.lib.cpu_util import check_cpu_util


def parse_bvip_util(string_table: StringTable) -> StringTable:
    return string_table


def discover_bvip_util(section: StringTable) -> DiscoveryResult:
    if section:
        for name in ["Total", "Coder", "VCA"]:
            yield Service(item=name)


def check_bvip_util(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    items = {
        "Total": 0,
        "Coder": 1,
        "VCA": 2,
    }

    usage = int(section[0][items[item]])
    if item == "Total":
        usage = 100 - usage
    yield from check_cpu_util(
        util=float(usage),
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


snmp_section_bvip_util = SimpleSNMPSection(
    name="bvip_util",
    detect=DETECT_BVIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3967.1.1.9.1",
        oids=["1", "2", "3"],
    ),
    parse_function=parse_bvip_util,
)


check_plugin_bvip_util = CheckPlugin(
    name="bvip_util",
    service_name="CPU utilization %s",
    discovery_function=discover_bvip_util,
    check_function=check_bvip_util,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={"levels": (90.0, 95.0)},
)

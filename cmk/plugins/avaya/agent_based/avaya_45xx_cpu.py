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
    contains,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util


def parse_avaya_45xx_cpu(string_table: StringTable) -> StringTable:
    return string_table


def discover_avaya_45xx_cpu(section: StringTable) -> DiscoveryResult:
    for idx, _line in enumerate(section):
        yield Service(item=str(idx))


def check_avaya_45xx_cpu(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    for idx, used_perc in enumerate(section):
        if str(idx) == item:
            yield from check_cpu_util(
                util=int(used_perc[0]),
                params=params,
                value_store=get_value_store(),
                this_time=time.time(),
            )
            return


snmp_section_avaya_45xx_cpu = SimpleSNMPSection(
    name="avaya_45xx_cpu",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.45.3"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.45.1.6.3.8.1.1.5",
        oids=["3"],
    ),
    parse_function=parse_avaya_45xx_cpu,
)


check_plugin_avaya_45xx_cpu = CheckPlugin(
    name="avaya_45xx_cpu",
    service_name="CPU utilization CPU %s",
    discovery_function=discover_avaya_45xx_cpu,
    check_function=check_avaya_45xx_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={"levels": (90.0, 95.0)},
)

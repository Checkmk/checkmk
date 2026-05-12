#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    any_of,
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


def parse_hp_procurve_cpu(string_table: StringTable) -> StringTable:
    return string_table


def discover_hp_procurve_cpu(section: StringTable) -> DiscoveryResult:
    if len(section) == 1 and 0 <= int(section[0][0]) <= 100:
        yield Service()


def check_hp_procurve_cpu(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    try:
        util = int(section[0][0])
    except (IndexError, ValueError):
        return

    if 0 <= util <= 100:
        yield from check_cpu_util(
            util=util,
            params=params,
            value_store=get_value_store(),
            this_time=time.time(),
        )


snmp_section_hp_procurve_cpu = SimpleSNMPSection(
    name="hp_procurve_cpu",
    detect=any_of(
        contains(".1.3.6.1.2.1.1.2.0", ".11.2.3.7.11"),
        contains(".1.3.6.1.2.1.1.2.0", ".11.2.3.7.8"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.14.11.5.1.9.6",
        oids=["1"],
    ),
    parse_function=parse_hp_procurve_cpu,
)


check_plugin_hp_procurve_cpu = CheckPlugin(
    name="hp_procurve_cpu",
    service_name="CPU utilization",
    discovery_function=discover_hp_procurve_cpu,
    check_function=check_hp_procurve_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)

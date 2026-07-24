#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
# Example Output:
# .1.3.6.1.4.1.5951.4.1.1.41.6.1.1.8.77.103.109.116.32.67.80.85  "Mgmt CPU"
# .1.3.6.1.4.1.5951.4.1.1.41.6.1.1.12.80.97.99.107.101.116.32.67.80.85.32.48  "Packet CPU 0"
# .1.3.6.1.4.1.5951.4.1.1.41.6.1.2.8.77.103.109.116.32.67.80.85  0
# .1.3.6.1.4.1.5951.4.1.1.41.6.1.2.12.80.97.99.107.101.116.32.67.80.85.32.48  0


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
from cmk.plugins.lib.cpu_util import check_cpu_util
from cmk.plugins.netscaler.agent_based.lib import SNMP_DETECT


def discover_netscaler_cpu(section: StringTable) -> DiscoveryResult:
    for cpu_name, _cpu_usage in section:
        yield Service(item=cpu_name)


def check_netscaler_cpu(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    for cpu_name, cpu_usage in section:
        if cpu_name == item:
            yield from check_cpu_util(
                util=float(cpu_usage),
                params=params,
                value_store=get_value_store(),
                this_time=time.time(),
            )
            return


def parse_netscaler_cpu(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_netscaler_cpu = SimpleSNMPSection(
    name="netscaler_cpu",
    detect=SNMP_DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5951.4.1.1.41.6.1",
        oids=["1", "2"],
    ),
    parse_function=parse_netscaler_cpu,
)


check_plugin_netscaler_cpu = CheckPlugin(
    name="netscaler_cpu",
    service_name="CPU Utilization %s",
    discovery_function=discover_netscaler_cpu,
    check_function=check_netscaler_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={"levels": (90.0, 95.0)},
)

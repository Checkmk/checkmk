#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

#
# Example Output:
# .1.3.6.1.4.1.5951.4.1.1.41.6.1.1.8.77.103.109.116.32.67.80.85  "Mgmt CPU"
# .1.3.6.1.4.1.5951.4.1.1.41.6.1.1.12.80.97.99.107.101.116.32.67.80.85.32.48  "Packet CPU 0"
# .1.3.6.1.4.1.5951.4.1.1.41.6.1.2.8.77.103.109.116.32.67.80.85  0
# .1.3.6.1.4.1.5951.4.1.1.41.6.1.2.12.80.97.99.107.101.116.32.67.80.85.32.48  0


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, SNMPTree, StringTable
from cmk.plugins.netscaler.agent_based.lib import SNMP_DETECT

check_info = {}


def discover_netscaler_cpu(info):
    for cpu_name, _cpu_usage in info:
        yield cpu_name, {}


def check_netscaler_cpu(item, params, info):
    for cpu_name, cpu_usage in info:
        if cpu_name == item:
            cpu_usage = int(cpu_usage)

            return check_levels(
                cpu_usage,
                "load",
                params["levels"],
                human_readable_func=render.percent,
                infoname="CPU",
            )
    return None


def parse_netscaler_cpu(string_table: StringTable) -> StringTable:
    return string_table


check_info["netscaler_cpu"] = LegacyCheckDefinition(
    name="netscaler_cpu",
    parse_function=parse_netscaler_cpu,
    detect=SNMP_DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5951.4.1.1.41.6.1",
        oids=["1", "2"],
    ),
    service_name="CPU Utilization %s",
    discovery_function=discover_netscaler_cpu,
    check_function=check_netscaler_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={"levels": (90.0, 95.0)},
)

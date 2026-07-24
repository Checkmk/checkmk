#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
# Example Output:
# .1.3.6.1.4.1.5951.4.1.1.53.1.1.0  13
# .1.3.6.1.4.1.5951.4.1.1.53.1.2.0  11


import time
from collections.abc import Mapping

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.netscaler.agent_based.lib import SNMP_DETECT


def discover_netscaler_dnsrates(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_netscaler_dnsrates(
    params: Mapping[str, tuple[float, float]], section: StringTable
) -> CheckResult:
    queries, answers = map(int, section[0])

    now = time.time()
    value_store = get_value_store()
    for name, counter in (("query", queries), ("answer", answers)):
        rate = get_rate(value_store, name, now, counter, raise_overflow=True)
        yield from check_levels(
            rate,
            levels_upper=("fixed", params[name]),
            metric_name=f"{name}_rate",
            render_func=lambda x: f"{x:.1f}/sec",
            label=f"{name} rate",
        )


def parse_netscaler_dnsrates(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_netscaler_dnsrates = SimpleSNMPSection(
    name="netscaler_dnsrates",
    detect=SNMP_DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5951.4.1.1.53.1",
        oids=["1", "2"],
    ),
    parse_function=parse_netscaler_dnsrates,
)


check_plugin_netscaler_dnsrates = CheckPlugin(
    name="netscaler_dnsrates",
    service_name="DNS rates",
    discovery_function=discover_netscaler_dnsrates,
    check_function=check_netscaler_dnsrates,
    check_ruleset_name="netscaler_dnsrates",
    check_default_parameters={
        "query": (1500.0, 2000.0),
        "answer": (1500.0, 2000.0),
    },
)

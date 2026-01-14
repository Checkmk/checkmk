#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

#
# Example Output:
# .1.3.6.1.4.1.5951.4.1.1.53.1.1.0  13
# .1.3.6.1.4.1.5951.4.1.1.53.1.2.0  11


import time

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, SNMPTree, StringTable
from cmk.plugins.netscaler.agent_based.lib import SNMP_DETECT

check_info = {}


def discover_netscaler_dnsrates(info):
    if info:
        return [(None, {})]
    return []


def check_netscaler_dnsrates(_no_item, params, info):
    queries, answers = map(int, info[0])

    now = time.time()
    value_store = get_value_store()
    for name, counter in [("query", queries), ("answer", answers)]:
        rate = get_rate(value_store, name, now, counter, raise_overflow=True)
        warn, crit = params[name]

        yield check_levels(
            rate,
            name + "_rate",
            (warn, crit),
            infoname=f"{name} rate",
            human_readable_func=lambda x: f"{x:.1f}/sec",
        )


def parse_netscaler_dnsrates(string_table: StringTable) -> StringTable:
    return string_table


check_info["netscaler_dnsrates"] = LegacyCheckDefinition(
    name="netscaler_dnsrates",
    parse_function=parse_netscaler_dnsrates,
    detect=SNMP_DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5951.4.1.1.53.1",
        oids=["1", "2"],
    ),
    service_name="DNS rates",
    discovery_function=discover_netscaler_dnsrates,
    check_function=check_netscaler_dnsrates,
    check_ruleset_name="netscaler_dnsrates",
    check_default_parameters={
        "query": (1500.0, 2000.0),
        "answer": (1500.0, 2000.0),
    },
)

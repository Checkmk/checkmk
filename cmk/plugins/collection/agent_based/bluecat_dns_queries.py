#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

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
from cmk.plugins.lib.bluecat import DETECT_BLUECAT


def inventory_bluecat_dns_queries(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_bluecat_dns_queries(section: StringTable) -> CheckResult:
    value_names = ["Success", "Referral", "NXRSet", "NXDomain", "Recursion", "Failure"]
    value_store = get_value_store()
    now = time.time()
    for value, name in zip(section[0], value_names):
        rate = get_rate(
            value_store, f"bluecat_dns_queries.{name}", now, int(value), raise_overflow=True
        )
        yield from check_levels(rate, metric_name=name, label=name, render_func=str)


def parse_bluecat_dns_queries(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_bluecat_dns_queries = SimpleSNMPSection(
    name="bluecat_dns_queries",
    detect=DETECT_BLUECAT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13315.3.1.2.2.2.1",
        oids=["1", "2", "3", "4", "5", "6"],
    ),
    parse_function=parse_bluecat_dns_queries,
)
check_plugin_bluecat_dns_queries = CheckPlugin(
    name="bluecat_dns_queries",
    service_name="DNS Queries",
    discovery_function=inventory_bluecat_dns_queries,
    check_function=check_bluecat_dns_queries,
)

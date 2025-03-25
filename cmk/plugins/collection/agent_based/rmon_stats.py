#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This check extracts data from 1.3.6.1.2.1.16.1.1.1 =
# iso(1). org(3). dod(6). internet(1). mgmt(2). mib-2(1). rmon(16).
# statistics(1). etherStatsTable(1). etherStatsEntry(1)
# The MIB is called RMON-MIB

import time
from collections.abc import Mapping
from typing import Literal

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    exists,
    get_rate,
    get_value_store,
    GetRateError,
    IgnoreResults,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)

PortStats = Mapping[str, int]

_FIELDS = ["bcast", "mcast", "0-63b", "64-127b", "128-255b", "256-511b", "512-1023b", "1024-1518b"]


def parse_rmon_stats(string_table: StringTable) -> Mapping[str, PortStats]:
    return {
        port: {k: int(v.replace(" Packets", "")) for k, v in zip(_FIELDS, row)}
        for port, *row in string_table
    }


def discover_rmon_stats(
    params: Mapping[Literal["discover"], bool],
    section: Mapping[str, PortStats],
) -> DiscoveryResult:
    if params.get("discover", False):
        yield from (Service(item=item) for item in section)


def check_rmon_stats(item: str, section: Mapping[str, PortStats]) -> CheckResult:
    if (stats := section.get(item)) is None:
        return

    now = time.time()
    value_store = get_value_store()
    for metric, octets in stats.items():
        try:
            rate = get_rate(value_store, metric, now, octets)
        except GetRateError:
            yield IgnoreResults()
        else:
            yield from check_levels_v1(
                rate, metric_name=metric, render_func=lambda v: "%.0f octets/sec" % v, label=metric
            )


snmp_section_rmon_stats = SimpleSNMPSection(
    name="rmon_stats",
    parse_function=parse_rmon_stats,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.16.1.1.1",
        oids=[  #
            "1",  # etherStatsIndex = Item
            "6",  # etherStatsBroadcastPkts
            "7",  # etherStatsMulticastPkts
            "14",  # etherStatsPkts64Octets
            "15",  # etherStatsPkts65to127Octets
            "16",  # etherStatsPkts128to255Octets
            "17",  # etherStatsPkts256to511Octets
            "18",  # etherStatsPkts512to1023Octets
            "19",  # etherStatsPkts1024to1518Octets
        ],
    ),
    detect=all_of(
        any_of(
            startswith(".1.3.6.1.2.1.1.1.0", "cisco"),
            equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.11863.1.1.3"),
        ),
        # for the scan we need to check for any single object in the RMON tree,
        # we choose netDefaultGateway in the hope that it will always be present
        exists(".1.3.6.1.2.1.16.19.12.0"),
    ),
)

check_plugin_rmon_stats = CheckPlugin(
    name="rmon_stats",
    service_name="RMON Stats IF %s",
    discovery_function=discover_rmon_stats,
    discovery_ruleset_name="rmon_discovery",
    discovery_default_parameters={"discover": False},
    check_function=check_rmon_stats,
)

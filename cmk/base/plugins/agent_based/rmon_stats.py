#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This check extracts data from 1.3.6.1.2.1.16.1.1.1 =
# iso(1). org(3). dod(6). internet(1). mgmt(2). mib-2(1). rmon(16).
# statistics(1). etherStatsTable(1). etherStatsEntry(1)
# The MIB is called RMON-MIB

import time
from typing import Literal, Mapping

from .agent_based_api.v1 import (
    all_of,
    any_of,
    check_levels,
    equals,
    exists,
    get_rate,
    get_value_store,
    GetRateError,
    IgnoreResults,
    register,
    Service,
    SNMPTree,
    startswith,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

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
            yield from check_levels(
                rate, metric_name=metric, render_func=lambda v: "%.0f octets/sec" % v, label=metric
            )


register.snmp_section(
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
    # for the scan we need to check for any single object in the RMON tree,
    # we choose netDefaultGateway in the hope that it will always be present
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.1.0", "cisco"),
        all_of(
            equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.11863.1.1.3"),
            exists(".1.3.6.1.2.1.16.19.12.0"),
        ),
    ),
)

register.check_plugin(
    name="rmon_stats",
    service_name="RMON Stats IF %s",
    discovery_function=discover_rmon_stats,
    discovery_ruleset_name="rmon_discovery",
    discovery_default_parameters={"discover": False},
    check_function=check_rmon_stats,
)

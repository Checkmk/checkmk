#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# FIXME:
# - no camel case in check parameters
# - use friendly output of values. Output
#   "Ingress Dequeue Packets" instead of "brcdTMStatsIngressDequeuePkts"


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
from cmk.plugins.brocade.lib import DETECT_MLX

_LEVELS = (1000.0, 10000.0)

_COUNTERS = (
    "TotalIngressPktsCnt",
    "IngressEnqueuePkts",
    "EgressEnqueuePkts",
    "IngressDequeuePkts",
    "IngressTotalQDiscardPkts",
    "IngressOldestDiscardPkts",
    "EgressDiscardPkts",
)


def parse_brocade_tm(string_table: StringTable) -> StringTable:
    return string_table


def discover_brocade_tm(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0])


def check_brocade_tm(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if line[0] != item:
            continue
        now = time.time()
        value_store = get_value_store()
        for name, counter in zip(_COUNTERS, line[1:]):
            rate = get_rate(value_store, f"{name}.{item}", now, int(counter), raise_overflow=True)
            metric_name = f"brcdTMStats{name}"
            if "Discard" in name:
                yield from check_levels(
                    rate,
                    metric_name=metric_name,
                    levels_upper=("fixed", _LEVELS),
                    label=name,
                    render_func=lambda v: f"{v:.1f}",
                )
            else:
                yield from check_levels(
                    rate,
                    metric_name=metric_name,
                    label=name,
                    render_func=lambda v: f"{v:.1f}",
                )
        return


snmp_section_brocade_tm = SimpleSNMPSection(
    name="brocade_tm",
    detect=DETECT_MLX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1991.1.14.2.1.2.2.1",
        oids=["3", "4", "5", "6", "9", "11", "13", "15"],
    ),
    parse_function=parse_brocade_tm,
)


check_plugin_brocade_tm = CheckPlugin(
    name="brocade_tm",
    service_name="TM %s",
    discovery_function=discover_brocade_tm,
    check_function=check_brocade_tm,
)

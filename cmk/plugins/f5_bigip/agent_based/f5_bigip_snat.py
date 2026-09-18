#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    LevelsT,
    Metric,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.f5_bigip.lib import F5_BIGIP

_NO_LEVELS: LevelsT[float] = ("no_levels", None)

# The order the counters appear in the SNMP row, and the order their metrics are reported in.
_COUNTERS = (
    "if_in_pkts",
    "if_out_pkts",
    "if_in_octets",
    "if_out_octets",
    "connections_rate",
    "connections",
)

# The counters that are rates; "connections" is a gauge and only ever summed.
_RATE_COUNTERS = _COUNTERS[:-1]

_TRAFFIC_LABELS = {
    "if_in_octets": "Incoming Bytes",
    "if_out_octets": "Outgoing Bytes",
    "if_total_octets": "Total Bytes",
    "if_in_pkts": "Incoming Packets",
    "if_out_pkts": "Outgoing Packets",
    "if_total_pkts": "Total Packets",
}


# The parameter keys are the counter names below, each optionally suffixed with
# "_lower"; see cmk/plugins/f5_bigip/rulesets/f5_bigip_snat.py.
type SnatParams = Mapping[str, LevelsT[float]]


type SnatCounters = Mapping[str, Sequence[int]]
Section = Mapping[str, SnatCounters]


def parse_f5_bigip_snat(string_table: StringTable) -> Section:
    snats: dict[str, dict[str, list[int]]] = {}
    for line in string_table:
        name, *values = line
        counters = snats.setdefault(name, {})
        for counter, value in zip(_COUNTERS, values, strict=False):
            # The columns of OIDs the device does not answer are empty. Every other value
            # is a counter and has to be a number; one that is not means the device
            # violated the MIB, which we let crash rather than silently drop.
            if not value:
                continue
            counters.setdefault(counter, []).append(int(value))
    return {name: counters for name, counters in snats.items() if counters}


def discover_f5_bigip_snat(section: Section) -> DiscoveryResult:
    yield from (Service(item=name) for name in section)


def check_f5_bigip_snat(item: str, params: SnatParams, section: Section) -> CheckResult:
    if (snat := section.get(item)) is None:
        return

    value_store = get_value_store()
    now = time.time()

    summed: dict[str, float] = {}
    for counter in _RATE_COUNTERS:
        summed[counter] = sum(
            get_rate(value_store, f"{counter}.{index}", now, value, raise_overflow=True)
            for index, value in enumerate(snat.get(counter, ()))
        )
    summed["connections"] = sum(snat.get("connections", ()))

    # Current number of connections
    yield Result(state=State.OK, summary=f"Client connections: {summed['connections']:.0f}")
    yield from (Metric(counter, summed[counter]) for counter in _COUNTERS)

    # New connections per time
    yield Result(state=State.OK, summary=f"Rate: {summed['connections_rate']:.2f}/sec")

    summed["if_total_octets"] = summed["if_in_octets"] + summed["if_out_octets"]
    summed["if_total_pkts"] = summed["if_in_pkts"] + summed["if_out_pkts"]

    for counter, label in _TRAFFIC_LABELS.items():
        levels_upper = params.get(counter)
        levels_lower = params.get(f"{counter}_lower")
        if levels_upper is None and levels_lower is None:
            continue

        yield from check_levels(
            summed[counter],
            levels_upper=levels_upper or _NO_LEVELS,
            levels_lower=levels_lower or _NO_LEVELS,
            render_func=render.disksize if "octets" in counter else str,
            label=label,
            notice_only=True,
        )


snmp_section_f5_bigip_snat = SimpleSNMPSection(
    name="f5_bigip_snat",
    detect=F5_BIGIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.2.9.2.3.1",
        # The name, followed by the counters listed in _COUNTERS.
        oids=["1", "2", "3", "4", "5", "7", "8"],
    ),
    parse_function=parse_f5_bigip_snat,
)


check_plugin_f5_bigip_snat = CheckPlugin(
    name="f5_bigip_snat",
    service_name="Source NAT %s",
    discovery_function=discover_f5_bigip_snat,
    check_function=check_f5_bigip_snat,
    check_ruleset_name="f5_bigip_snat",
    check_default_parameters={},
)

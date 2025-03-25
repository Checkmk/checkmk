#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import NamedTuple

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


class WaterflowReading(NamedTuple):
    name: str
    status: str
    unit: str
    flow: float
    minflow: float
    maxflow: float


Section = WaterflowReading


def parse_cmciii_lcp_waterflow(string_table: StringTable) -> Section | None:
    if not string_table:
        return None

    # We have a list of values where no item has a fixed index. We
    # try to detect the starting index for the needed values now.
    iter_info = iter(string_table[0])
    name = None
    for line in iter_info:
        if "Waterflow" in line:
            name = line
            break

    if name is None:
        return None

    flow, unit = next(iter_info).split(" ", 1)
    maxflow = next(iter_info).split(" ", 1)[0]
    minflow = next(iter_info).split(" ", 1)[0]
    status = next(iter_info)

    return WaterflowReading(
        name=name,
        status=status,
        unit=unit,
        flow=float(flow),
        minflow=float(minflow),
        maxflow=float(maxflow),
    )


def inventory_cmciii_lcp_waterflow(section: Section) -> DiscoveryResult:
    yield Service()


def check_cmciii_lcp_waterflow(section: Section) -> CheckResult:
    state = State.OK
    if section.status != "OK":
        state = State.CRIT
    elif section.flow < section.minflow or section.flow > section.maxflow:
        state = State.WARN

    yield Result(state=State.OK, summary=f"{section.name} Status: {section.status}")
    yield Result(state=state, summary=f"Flow: {section.flow:.1f}")
    yield Result(state=State.OK, summary=f"MinFlow: {section.minflow:.1f}")
    yield Result(state=State.OK, summary=f"MaxFlow: {section.maxflow:.1f}")

    yield Metric("flow", section.flow, levels=(section.maxflow, float("inf")))


snmp_section_cmciii_lcp_waterflow = SimpleSNMPSection(
    name="cmciii_lcp_waterflow",
    detect=startswith(".1.3.6.1.2.1.1.1.0", "Rittal LCP"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2606.7.4.2.2.1.10.2",
        oids=["74", "75", "76", "77", "78", "79", "80", "81", "82", "83", "84", "85", "86", "87"],
    ),
    parse_function=parse_cmciii_lcp_waterflow,
)


check_plugin_cmciii_lcp_waterflow = CheckPlugin(
    name="cmciii_lcp_waterflow",
    service_name="LCP Fanunit WATER FLOW",
    discovery_function=inventory_cmciii_lcp_waterflow,
    check_function=check_cmciii_lcp_waterflow,
)

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)

linux_nic_check = "lnx_if"

netctr_counters = [
    "rx_bytes",
    "tx_bytes",
    "rx_packets",
    "tx_packets",
    "rx_errors",
    "tx_errors",
    "tx_collisions",
]

# Check counters from network interfaces
# Item is devicename.countername, eg,
# eth0.tx_collisions. Available are:

netctr_counter_indices = {
    # Receive
    "rx_bytes": 0,
    "rx_packets": 1,
    "rx_errors": 2,
    "rx_drop": 3,
    "rx_fifo": 4,
    "rx_frame": 5,
    "rx_compressed": 6,
    "rx_multicast": 7,
    # Transmit
    "tx_bytes": 8,
    "tx_packets": 9,
    "tx_errors": 10,
    "tx_drop": 11,
    "tx_fifo": 12,
    "tx_collisions": 13,
    "tx_carrier": 14,
    "tx_compressed": 15,
}


def discover_netctr_combined(section: StringTable) -> DiscoveryResult:
    if linux_nic_check != "legacy":
        return
    if len(section) == 0:
        return
    for line in section[1:]:
        if line[0] != "lo" and not line[0].startswith("sit"):
            yield Service(item=line[0])


def check_netctr_combined(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    warn, crit = params["levels"]
    this_time = int(section[0][0])
    value_store = get_value_store()

    # Look for line describing this nic
    for nicline in section[1:]:
        if nicline[0] != item:
            continue
        metrics: list[Metric] = []
        infotxt = ""
        problems_per_sec = 0.0
        packets_per_sec = 0.0
        for countername in netctr_counters:
            index = netctr_counter_indices[countername]
            value = int(nicline[index + 1])
            items_per_sec = get_rate(
                value_store, f"netctr.{item}.{countername}", this_time, value, raise_overflow=True
            )
            metrics.append(Metric(countername, value))

            if countername in ["rx_errors", "tx_errors", "tx_collisions"]:
                problems_per_sec += items_per_sec
            elif countername in ["rx_packets", "tx_packets"]:
                packets_per_sec += items_per_sec
            if countername == "rx_bytes":
                infotxt += f" - Receive: {items_per_sec / (1024 * 1024):.2f} MB/sec"
            elif countername == "tx_bytes":
                infotxt += f" - Send: {items_per_sec / (1024 * 1024):.2f} MB/sec"

        error_percentage = 0.0
        if problems_per_sec > 0:
            error_percentage = (problems_per_sec / packets_per_sec) * 100.0
            infotxt += f", error rate {error_percentage:.4f}%"
        if error_percentage >= crit:
            yield Result(state=State.CRIT, summary=infotxt)
        elif error_percentage >= warn:
            yield Result(state=State.WARN, summary=infotxt)
        else:
            yield Result(state=State.OK, summary=infotxt)
        yield from metrics
        return

    yield Result(state=State.UNKNOWN, summary="NIC is not present")


def parse_netctr(string_table: StringTable) -> StringTable:
    return string_table


agent_section_netctr = AgentSection(
    name="netctr",
    parse_function=parse_netctr,
)


check_plugin_netctr_combined = CheckPlugin(
    name="netctr_combined",
    service_name="NIC %s counters",
    sections=["netctr"],
    discovery_function=discover_netctr_combined,
    check_function=check_netctr_combined,
    check_default_parameters={"levels": (0.01, 0.1)},
)

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, StringTable

check_info = {}

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


def discover_netctr_combined(info):
    if linux_nic_check != "legacy":
        return []
    if len(info) == 0:
        return []
    return [(l[0], {}) for l in info[1:] if l[0] != "lo" and not l[0].startswith("sit")]


def check_netctr_combined(nic, params, info):
    warn, crit = params["levels"]
    this_time = int(info[0][0])
    value_store = get_value_store()

    # Look for line describing this nic
    for nicline in info[1:]:
        if nicline[0] != nic:
            continue
        perfdata = []
        infotxt = ""
        problems_per_sec = 0.0
        packets_per_sec = 0.0
        for countername in netctr_counters:
            index = netctr_counter_indices[countername]
            value = int(nicline[index + 1])
            items_per_sec = get_rate(
                value_store, f"netctr.{nic}.{countername}", this_time, value, raise_overflow=True
            )
            perfdata.append((countername, "%dc" % value))

            if countername in ["rx_errors", "tx_errors", "tx_collisions"]:
                problems_per_sec += items_per_sec
            elif countername in ["rx_packets", "tx_packets"]:
                packets_per_sec += items_per_sec
            if countername == "rx_bytes":
                infotxt += " - Receive: %.2f MB/sec" % (float(items_per_sec) / float(1024 * 1024))
            elif countername == "tx_bytes":
                infotxt += " - Send: %.2f MB/sec" % (float(items_per_sec) / float(1024 * 1024))

        error_percentage = 0.0
        if problems_per_sec > 0:
            error_percentage = (problems_per_sec / packets_per_sec) * 100.0  # fixed: true-division
            infotxt += ", error rate %.4f%%" % error_percentage
        if error_percentage >= crit:
            return (2, infotxt, perfdata)
        if error_percentage >= warn:
            return (1, infotxt, perfdata)
        return (0, infotxt, perfdata)

    return (3, "NIC is not present")


def parse_netctr(string_table: StringTable) -> StringTable:
    return string_table


check_info["netctr"] = LegacyCheckDefinition(
    name="netctr",
    parse_function=parse_netctr,
)

check_info["netctr.combined"] = LegacyCheckDefinition(
    name="netctr_combined",
    service_name="NIC %s counters",
    sections=["netctr"],
    discovery_function=discover_netctr_combined,
    check_function=check_netctr_combined,
    check_default_parameters={"levels": (0.01, 0.1)},
)

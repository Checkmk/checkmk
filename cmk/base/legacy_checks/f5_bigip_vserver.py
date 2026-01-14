#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"


import socket
import time

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, GetRateError, render, SNMPTree
from cmk.plugins.f5_bigip.lib import F5_BIGIP

check_info = {}

# Current server status
# vserver["status"]
# 0 - NONE:   disabled
# 1 - GREEN:  available in some capacity
# 2 - YELLOW: not currently available
# 3 - RED:    not available
# 4 - BLUE:   availability is unknown
# 5 - GREY:   unlicensed
MAP_SERVER_STATUS = {
    "0": (1, "is disabled"),
    "1": (0, "is up and available"),
    "2": (2, "is currently not available"),
    "3": (2, "is not available"),
    "4": (1, "availability is unknown"),
    "5": (3, "is unlicensed"),
}

MAP_ENABLED = {
    "0": "NONE",
    "1": "enabled",
    "2": "disabled",
    "3": "disabled by parent",
}

# Check configured limits
MAP_PARAM_TO_TEXT = {
    "if_in_octets": "Incoming bytes",
    "if_out_octets": "Outgoing bytes",
    "if_total_octets": "Total bytes",
    "if_in_pkts": "Incoming packets",
    "if_out_pkts": "Outgoing packets",
    "if_total_pkts": "Total packets",
}


def get_ip_address_human_readable(ip_addr):
    """
    u'\xc2;xJ'  ->  '194.59.120.74'
    """
    try:
        ip_addr_binary = bytes(ord(x) for x in ip_addr)
    except ValueError:
        return "-"

    if len(ip_addr_binary) == 4:
        return socket.inet_ntop(socket.AF_INET, ip_addr_binary)
    if len(ip_addr_binary) == 16:
        return socket.inet_ntop(socket.AF_INET6, ip_addr_binary)
    return "-"


def parse_f5_bigip_vserver(string_table):
    vservers: dict[str, dict] = {}
    for line in string_table:
        instance = vservers.setdefault(
            line[0],
            {
                "status": line[1],
                "enabled": line[2],
                "detail": line[3],
                "ip_address": get_ip_address_human_readable(line[4]),
            },
        )

        for key, index, factor in [
            ("connections_duration_min", 5, 0.001),
            ("connections_duration_max", 6, 0.001),
            ("connections_duration_mean", 7, 0.001),
            ("if_in_pkts", 8, 1),
            ("if_out_pkts", 9, 1),
            ("if_in_octets", 10, 1),
            ("if_out_octets", 11, 1),
            ("connections_rate", 12, 1),
            ("connections", 13, 1),
            ("packet_velocity_asic", 14, 1),
        ]:
            try:
                value = int(line[index]) * factor
            except (IndexError, ValueError):
                continue
            instance.setdefault(key, []).append(value)
    return vservers


def discover_f5_bigip_vserver(parsed):
    for name in parsed:
        yield name, {}


_AGGREGATION_KEYS = {
    "if_in_pkts",
    "if_out_pkts",
    "if_in_octets",
    "if_out_octets",
    "connections_rate",
    "packet_velocity_asic",
}


def get_aggregated_values(vserver):
    value_store = get_value_store()
    now = time.time()

    aggregation: dict[str, float] = {}

    # Calculate counters
    for what in _AGGREGATION_KEYS.intersection(vserver):
        this_aggregation = 0.0
        raised = False
        for idx, entry in enumerate(vserver[what]):
            try:
                this_aggregation += get_rate(
                    value_store, f"{what}.{idx}", now, entry, raise_overflow=True
                )
            except GetRateError:
                raised = True
        if not raised:
            aggregation[what] = this_aggregation

    # Calucate min/max/sum/mean values
    for what, function in [
        ("connections_duration_min", lambda x: float(min(x))),
        ("connections_duration_max", lambda x: float(max(x))),
        ("connections", lambda x: float(sum(x))),
        ("connections_duration_mean", lambda x: float(sum(x)) / len(x)),
    ]:
        value_list = vserver.get(what)
        if value_list:
            aggregation[what] = function(value_list)

    for unit in ("octets", "pkts"):
        in_key = "if_in_%s" % unit
        out_key = "if_out_%s" % unit
        if in_key in aggregation or out_key in aggregation:
            aggregation["if_total_%s" % unit] = aggregation.get(in_key, 0.0) + aggregation.get(
                out_key, 0.0
            )

    return aggregation


def iter_counter_params():
    for unit, hr_function in (
        ("octets", render.iobandwidth),
        ("pkts", lambda x: "%s/s" % x),
    ):
        for direction in ("in", "out", "total"):
            for boundary in ("", "_lower"):
                yield direction, unit, boundary, hr_function


def check_f5_bigip_vserver(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    # Need compatibility to version with _no_params
    if params is None:
        params = {}

    enabled_state = int(data["enabled"] not in MAP_ENABLED)
    enabled_txt = MAP_ENABLED.get(data["enabled"], "in unknown state")
    yield enabled_state, "Virtual Server with IP {} is {}".format(data["ip_address"], enabled_txt)

    state_map = params.get("state", {})
    state, state_readable = MAP_SERVER_STATUS.get(
        data["status"], (3, "Unhandled status (%s)" % data["status"])
    )
    state = state_map.get(state_readable.replace(" ", "_"), state)

    detail = data["detail"]
    # Special handling: Statement from the network team:
    # Not available => uncritical when the childrens are down
    if data["status"] == "3" and detail.lower() == "the children pool member(s) are down":
        state = state_map.get("children_pool_members_down_if_not_available", 0)

    yield state, f"State {state_readable}, Detail: {detail}"

    aggregation = get_aggregated_values(data)

    if "connections" in aggregation:
        connections = aggregation["connections"]
        state = 0
        if "connections" in params and params["connections"]:
            warn, crit = params["connections"]
            if connections >= crit:
                state = 2
            elif connections >= warn:
                state = 1
        yield state, "Client connections: %d" % connections, sorted(aggregation.items())
    if "connections_rate" in aggregation:
        yield 0, "Connections rate: %.2f/sec" % aggregation["connections_rate"]

    for direction, unit, boundary, hr_function in iter_counter_params():
        key = f"if_{direction}_{unit}"
        levels = params.get(f"{key}{boundary}")
        if levels is None or key not in aggregation:
            continue
        if boundary == "_lower" and isinstance(levels, tuple):
            levels = (None, None) + levels
        state, infotext, _extra_perfdata = check_levels(
            aggregation[key],
            None,
            levels,
            human_readable_func=hr_function,
            infoname=MAP_PARAM_TO_TEXT[key],
        )
        if state:
            yield state, infotext


check_info["f5_bigip_vserver"] = LegacyCheckDefinition(
    name="f5_bigip_vserver",
    detect=F5_BIGIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.2.10",
        oids=[
            "13.2.1.1",
            "13.2.1.2",
            "13.2.1.3",
            "13.2.1.5",
            "1.2.1.3",
            "2.3.1.2",
            "2.3.1.3",
            "2.3.1.4",
            "2.3.1.6",
            "2.3.1.8",
            "2.3.1.7",
            "2.3.1.9",
            "2.3.1.11",
            "2.3.1.12",
            "2.3.1.25",
        ],
    ),
    parse_function=parse_f5_bigip_vserver,
    service_name="Virtual Server %s",
    discovery_function=discover_f5_bigip_vserver,
    check_function=check_f5_bigip_vserver,
    check_ruleset_name="f5_bigip_vserver",
)

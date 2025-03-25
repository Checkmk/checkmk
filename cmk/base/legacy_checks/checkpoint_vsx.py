#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

import time
from collections.abc import Callable

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, render, SNMPTree
from cmk.plugins.lib.detection import DETECT_NEVER

check_info = {}

# .1.3.6.1.4.1.2620.1.16.22.1.1.1.1.0 0
# .1.3.6.1.4.1.2620.1.16.22.1.1.2.1.0 0
# .1.3.6.1.4.1.2620.1.16.22.1.1.3.1.0 "my_vsid"
# .1.3.6.1.4.1.2620.1.16.22.1.1.4.1.0 "VSX Gateway"
# .1.3.6.1.4.1.2620.1.16.22.1.1.5.1.0 "192.168.1.11"
# .1.3.6.1.4.1.2620.1.16.22.1.1.6.1.0 "Standard"
# .1.3.6.1.4.1.2620.1.16.22.1.1.7.1.0 "Active"
# .1.3.6.1.4.1.2620.1.16.22.1.1.8.1.0 "Trust established"
# .1.3.6.1.4.1.2620.1.16.22.1.1.9.1.0 "Standby"
# .1.3.6.1.4.1.2620.1.16.22.1.1.10.1.0 0
# .1.3.6.1.4.1.2620.1.16.23.1.1.1.1.0 0
# .1.3.6.1.4.1.2620.1.16.23.1.1.2.1.0 104470
# .1.3.6.1.4.1.2620.1.16.23.1.1.3.1.0 120147
# .1.3.6.1.4.1.2620.1.16.23.1.1.4.1.0 499900
# .1.3.6.1.4.1.2620.1.16.23.1.1.5.1.0 150512
# .1.3.6.1.4.1.2620.1.16.23.1.1.6.1.0 369
# .1.3.6.1.4.1.2620.1.16.23.1.1.7.1.0 150143
# .1.3.6.1.4.1.2620.1.16.23.1.1.8.1.0 0
# .1.3.6.1.4.1.2620.1.16.23.1.1.9.1.0 46451524
# .1.3.6.1.4.1.2620.1.16.23.1.1.10.1.0 44344
# .1.3.6.1.4.1.2620.1.16.23.1.1.11.1.0 0
# .1.3.6.1.4.1.2620.1.16.23.1.1.12.1.0 2386
# .1.3.6.1.4.1.2620.1.16.23.1.1.13.1.0 1


def parse_checkpoint_vsx(string_table):
    parsed = {}
    status_table, counter_table = string_table

    vsid_info = [s + c for (s, c) in zip(status_table, counter_table)]

    for (
        vs_id,
        vs_name,
        vs_type,
        vs_ip,
        vs_policy,
        vs_policy_type,
        vs_sic_status,
        vs_ha_status,
        conn_num,
        conn_table_size,
        packets,
        packets_dropped,
        packets_accepted,
        packets_rejected,
        bytes_accepted,
        bytes_dropped,
        bytes_rejected,
        logged,
    ) in vsid_info:
        item = f"{vs_name} {vs_id}"
        parsed.setdefault(
            item,
            {
                "vs_name": vs_name,
                "vs_type": vs_type,
                "vs_sic_status": vs_sic_status,
                "vs_ha_status": vs_ha_status,
                "vs_ip": vs_ip,
                "vs_policy": vs_policy,
                "vs_policy_type": vs_policy_type,
            },
        )

        inst = parsed.setdefault(item, {})
        for key, value in [
            ("conn_num", conn_num),
            ("conn_table_size", conn_table_size),
            ("packets", packets),
            ("packets_dropped", packets_dropped),
            ("packets_accepted", packets_accepted),
            ("packets_rejected", packets_rejected),
            ("bytes_accepted", bytes_accepted),
            ("bytes_dropped", bytes_dropped),
            ("bytes_rejected", bytes_rejected),
            ("logged", logged),
        ]:
            try:
                inst[key] = int(value)
            except ValueError:
                pass

    return parsed


def discover_key(key: str) -> Callable:
    def discover_bound_keys(section):
        yield from ((item, {}) for item, data in section.items() if key in data)

    return discover_bound_keys


#   .--info----------------------------------------------------------------.
#   |                          _        __                                 |
#   |                         (_)_ __  / _| ___                            |
#   |                         | | '_ \| |_ / _ \                           |
#   |                         | | | | |  _| (_) |                          |
#   |                         |_|_| |_|_|  \___/                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_checkpoint_vsx(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return

    for key, infotext in [
        ("vs_type", "Type"),
        ("vs_ip", "Main IP"),
    ]:
        value = data.get(key)
        if value is None:
            continue

        yield 0, f"{infotext}: {value}"


check_info["checkpoint_vsx"] = LegacyCheckDefinition(
    name="checkpoint_vsx",
    detect=DETECT_NEVER,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2620.1.16.22.1.1",
            oids=["1", "3", "4", "5", "6", "7", "8", "9"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2620.1.16.23.1.1",
            oids=["2", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
        ),
    ],
    parse_function=parse_checkpoint_vsx,
    service_name="VS %s Info",
    discovery_function=discover_key("vs_name"),
    check_function=check_checkpoint_vsx,
)
# .
#   .--connections---------------------------------------------------------.
#   |                                        _   _                         |
#   |         ___ ___  _ __  _ __   ___  ___| |_(_) ___  _ __  ___         |
#   |        / __/ _ \| '_ \| '_ \ / _ \/ __| __| |/ _ \| '_ \/ __|        |
#   |       | (_| (_) | | | | | | |  __/ (__| |_| | (_) | | | \__ \        |
#   |        \___\___/|_| |_|_| |_|\___|\___|\__|_|\___/|_| |_|___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_checkpoint_vsx_connections(item, params, parsed):
    if not (data := parsed.get(item)):
        return

    conn_total = data.get("conn_num")
    if conn_total is None:
        return

    yield check_levels(
        conn_total,
        "connections",
        params.get("levels_abs"),
        human_readable_func=int,
        infoname="Used connections",
    )

    conn_limit = data.get("conn_table_size")
    if conn_limit is None:
        return

    if conn_limit > 0:
        yield check_levels(
            100.0 * conn_total / conn_limit,
            None,
            params.get("levels_perc"),
            human_readable_func=render.percent,
            infoname="Used percentage",
        )


check_info["checkpoint_vsx.connections"] = LegacyCheckDefinition(
    name="checkpoint_vsx_connections",
    service_name="VS %s Connections",
    sections=["checkpoint_vsx"],
    discovery_function=discover_key("conn_num"),
    check_function=check_checkpoint_vsx_connections,
    check_ruleset_name="checkpoint_vsx_connections",
    check_default_parameters={
        "levels_perc": (90.0, 95.0),
    },
)
# .
#   .--packets-------------------------------------------------------------.
#   |                                   _        _                         |
#   |                  _ __   __ _  ___| | _____| |_ ___                   |
#   |                 | '_ \ / _` |/ __| |/ / _ \ __/ __|                  |
#   |                 | |_) | (_| | (__|   <  __/ |_\__ \                  |
#   |                 | .__/ \__,_|\___|_|\_\___|\__|___/                  |
#   |                 |_|                                                  |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_checkpoint_vsx_packets(item, params, parsed):
    if not (data := parsed.get(item)):
        return

    value_store = get_value_store()

    for key, infotext in [
        ("packets", "Total number of packets processed"),
        ("packets_accepted", "Total number of accepted packets"),
        ("packets_dropped", "Total number of dropped packets"),
        ("packets_rejected", "Total number of rejected packets"),
        ("logged", "Total number of logs sent"),
    ]:
        value = data.get(key)
        if value is None:
            continue

        this_time = int(time.time())
        value_per_sec = get_rate(
            value_store, "%s_rate" % key, this_time, value, raise_overflow=True
        )

        yield check_levels(
            value_per_sec,
            key,
            params.get(key),
            human_readable_func=int,
            infoname=infotext,
            unit="1/s",
        )


check_info["checkpoint_vsx.packets"] = LegacyCheckDefinition(
    name="checkpoint_vsx_packets",
    service_name="VS %s Packets",
    sections=["checkpoint_vsx"],
    discovery_function=discover_key("packets"),
    check_function=check_checkpoint_vsx_packets,
    check_ruleset_name="checkpoint_vsx_packets",
)
# .
#   .--traffic-------------------------------------------------------------.
#   |                    _              __  __ _                           |
#   |                   | |_ _ __ __ _ / _|/ _(_) ___                      |
#   |                   | __| '__/ _` | |_| |_| |/ __|                     |
#   |                   | |_| | | (_| |  _|  _| | (__                      |
#   |                    \__|_|  \__,_|_| |_| |_|\___|                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_checkpoint_vsx_traffic(item, params, parsed):
    if not (data := parsed.get(item)):
        return

    value_store = get_value_store()

    for key in [
        ("bytes_accepted"),
        ("bytes_dropped"),
        ("bytes_rejected"),
    ]:
        value = data.get(key)
        if value is None:
            continue

        this_time = int(time.time())
        value_per_sec = get_rate(value_store, f"{key}_rate", this_time, value, raise_overflow=True)

        yield check_levels(
            value_per_sec,
            key,
            params.get(key),
            human_readable_func=render.iobandwidth,
            infoname="Total number of %s" % key.replace("_", " "),
        )


check_info["checkpoint_vsx.traffic"] = LegacyCheckDefinition(
    name="checkpoint_vsx_traffic",
    service_name="VS %s Traffic",
    sections=["checkpoint_vsx"],
    discovery_function=discover_key("bytes_accepted"),
    check_function=check_checkpoint_vsx_traffic,
    check_ruleset_name="checkpoint_vsx_traffic",
)
# .
#   .--status--------------------------------------------------------------.
#   |                         _        _                                   |
#   |                     ___| |_ __ _| |_ _   _ ___                       |
#   |                    / __| __/ _` | __| | | / __|                      |
#   |                    \__ \ || (_| | |_| |_| \__ \                      |
#   |                    |___/\__\__,_|\__|\__,_|___/                      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_checkpoint_vsx_status(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return

    ha_state = data.get("vs_ha_status")
    if ha_state is not None:
        state = 0
        if ha_state.lower() not in ["active", "standby"]:
            state = 2

        yield state, "HA Status: %s" % ha_state

    sic_state = data.get("vs_sic_status")
    if sic_state is not None:
        state = 0
        if sic_state.lower() != "trust established":
            state = 2

        yield state, "SIC Status: %s" % sic_state

    policy_name = data.get("vs_policy")
    if policy_name is not None:
        yield 0, "Policy name: %s" % policy_name

    policy_type = data.get("vs_policy_type")
    if policy_type is not None:
        state = 0
        infotext = "Policy type: %s" % policy_type
        if policy_type.lower() not in ["active", "initial policy"]:
            state = 2
            infotext += " (no policy installed)"
        yield state, infotext


check_info["checkpoint_vsx.status"] = LegacyCheckDefinition(
    name="checkpoint_vsx_status",
    service_name="VS %s Status",
    sections=["checkpoint_vsx"],
    discovery_function=discover_key("vs_ha_status"),
    check_function=check_checkpoint_vsx_status,
)
# .

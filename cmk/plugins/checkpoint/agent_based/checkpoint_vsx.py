#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    render,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.checkpoint import DETECT

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


@dataclass(frozen=True)
class _Instance:
    vs_name: str
    vs_type: str
    vs_sic_status: str
    vs_ha_status: str
    vs_ip: str
    vs_policy: str
    vs_policy_type: str
    conn_num: int | None
    conn_table_size: int | None
    packets: int | None
    packets_dropped: int | None
    packets_accepted: int | None
    packets_rejected: int | None
    packets_logged: int | None
    bytes_accepted: int | None
    bytes_dropped: int | None
    bytes_rejected: int | None


type Section = Mapping[str, _Instance]


def _opt_int(raw: str) -> int | None:
    try:
        return int(raw)
    except ValueError:
        return None


def parse_checkpoint_vsx(string_table: Sequence[StringTable]) -> Section:
    status_table, counter_table = string_table

    # refactoring: first item occurence used to win. not sure if it matters
    vsid_info = reversed([s + c for (s, c) in zip(status_table, counter_table)])

    return {
        f"{vs_name} {vs_id}": _Instance(
            vs_name=vs_name,
            vs_type=vs_type,
            vs_sic_status=vs_sic_status,
            vs_ha_status=vs_ha_status,
            vs_ip=vs_ip,
            vs_policy=vs_policy,
            vs_policy_type=vs_policy_type,
            conn_num=_opt_int(conn_num),
            conn_table_size=_opt_int(conn_table_size),
            packets=_opt_int(packets),
            packets_dropped=_opt_int(packets_dropped),
            packets_accepted=_opt_int(packets_accepted),
            packets_rejected=_opt_int(packets_rejected),
            packets_logged=_opt_int(logged),
            bytes_accepted=_opt_int(bytes_accepted),
            bytes_dropped=_opt_int(bytes_dropped),
            bytes_rejected=_opt_int(bytes_rejected),
        )
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
        ) in vsid_info
    }


def discover_checkpoint_vsx(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


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


def check_checkpoint_vsx(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return

    yield Result(state=State.OK, summary=f"Type: {data.vs_type}")
    yield Result(state=State.OK, summary=f"Main IP: {data.vs_ip}")


snmp_section_checkpoint_vsx = SNMPSection(
    name="checkpoint_vsx",
    detect=DETECT,
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
)


check_plugin_checkpoint_vsx = CheckPlugin(
    name="checkpoint_vsx",
    service_name="VS %s Info",
    discovery_function=discover_checkpoint_vsx,
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


def discover_vsx_connections(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item, data in section.items() if data.conn_num is not None)


def check_checkpoint_vsx_connections(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return

    conn_total = data.conn_num
    if conn_total is None:
        return

    yield from check_levels(
        conn_total,
        metric_name="connections",
        levels_upper=params.get("levels_abs"),
        render_func=str,
        label="Used",
    )

    conn_limit = data.conn_table_size
    if conn_limit is None:
        return

    if conn_limit > 0:
        yield from check_levels(
            100.0 * conn_total / conn_limit,
            levels_upper=params.get("levels_perc"),
            render_func=render.percent,
        )


check_plugin_checkpoint_vsx_connections = CheckPlugin(
    name="checkpoint_vsx_connections",
    service_name="VS %s Connections",
    sections=["checkpoint_vsx"],
    discovery_function=discover_vsx_connections,
    check_function=check_checkpoint_vsx_connections,
    check_ruleset_name="checkpoint_vsx_connections",
    check_default_parameters={
        "levels_perc": ("fixed", (90.0, 95.0)),
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


def discover_vsx_packets(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item, data in section.items() if data.packets is not None)


def check_checkpoint_vsx_packets(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return

    value_store = get_value_store()

    for key, label, value in [
        ("packets", "Total number of packets processed", data.packets),
        ("packets_accepted", "Total number of accepted packets", data.packets_accepted),
        ("packets_dropped", "Total number of dropped packets", data.packets_dropped),
        ("packets_rejected", "Total number of rejected packets", data.packets_rejected),
        ("packets_logged", "Total number of logs sent", data.packets_logged),
    ]:
        if value is None:
            continue

        this_time = int(time.time())
        value_per_sec = get_rate(
            value_store, "%s_rate" % key, this_time, value, raise_overflow=True
        )

        yield from check_levels(
            value_per_sec,
            metric_name=key,
            levels_upper=params[key],
            render_func=lambda x: f"{x}/s",
            label=label,
        )


check_plugin_checkpoint_vsx_packets = CheckPlugin(
    name="checkpoint_vsx_packets",
    service_name="VS %s Packets",
    sections=["checkpoint_vsx"],
    discovery_function=discover_vsx_packets,
    check_function=check_checkpoint_vsx_packets,
    check_ruleset_name="checkpoint_vsx_packets",
    check_default_parameters={
        "packets": ("no_levels", None),
        "packets_accepted": ("no_levels", None),
        "packets_dropped": ("no_levels", None),
        "packets_rejected": ("no_levels", None),
        "packets_logged": ("no_levels", None),
    },
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


def discover_vsx_traffic(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item) for item, data in section.items() if data.bytes_accepted is not None
    )


def check_checkpoint_vsx_traffic(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return

    value_store = get_value_store()

    for key, value in [
        ("bytes_accepted", data.bytes_accepted),
        ("bytes_dropped", data.bytes_dropped),
        ("bytes_rejected", data.bytes_rejected),
    ]:
        if value is None:
            continue

        this_time = int(time.time())
        value_per_sec = get_rate(value_store, f"{key}_rate", this_time, value, raise_overflow=True)

        yield from check_levels(
            value_per_sec,
            metric_name=key,
            levels_upper=params[key],
            render_func=render.iobandwidth,
            label="Total number of %s" % key.replace("_", " "),
        )


check_plugin_checkpoint_vsx_traffic = CheckPlugin(
    name="checkpoint_vsx_traffic",
    service_name="VS %s Traffic",
    sections=["checkpoint_vsx"],
    discovery_function=discover_vsx_traffic,
    check_function=check_checkpoint_vsx_traffic,
    check_ruleset_name="checkpoint_vsx_traffic",
    check_default_parameters={
        "bytes_accepted": ("no_levels", None),
        "bytes_dropped": ("no_levels", None),
        "bytes_rejected": ("no_levels", None),
    },
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


def check_checkpoint_vsx_status(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return

    ha_state = data.vs_ha_status
    yield Result(
        state=State.CRIT if ha_state.lower() not in ["active", "standby"] else State.OK,
        summary="HA Status: %s" % ha_state,
    )

    sic_state = data.vs_sic_status
    yield Result(
        state=State.CRIT if sic_state.lower() != "trust established" else State.OK,
        summary="SIC Status: %s" % sic_state,
    )

    yield Result(state=State.OK, summary="Policy name: %s" % data.vs_policy)

    policy_type = data.vs_policy_type
    state = State.OK
    infotext = "Policy type: %s" % policy_type
    if policy_type.lower() not in ["active", "initial policy"]:
        state = State.CRIT
        infotext += " (no policy installed)"
    yield Result(state=state, summary=infotext)


check_plugin_checkpoint_vsx_status = CheckPlugin(
    name="checkpoint_vsx_status",
    service_name="VS %s Status",
    sections=["checkpoint_vsx"],
    discovery_function=discover_checkpoint_vsx,
    check_function=check_checkpoint_vsx_status,
)
# .

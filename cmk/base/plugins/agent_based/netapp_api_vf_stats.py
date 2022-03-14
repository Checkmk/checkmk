#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, Mapping, MutableMapping, Optional

from .agent_based_api.v1 import (
    check_levels,
    get_rate,
    get_value_store,
    GetRateError,
    IgnoreResultsError,
    register,
    render,
    Result,
    Service,
)
from .agent_based_api.v1 import State as state
from .agent_based_api.v1 import type_defs
from .utils import cpu_util, netapp_api

# <<<netapp_api_vf_stats:sep(9)>>>
# vfiler vfiler0 instance_uuid   node_uuid       vfiler_cpu_busy 663312444303217 vfiler_net_data_sent 8204762    vfiler_read_ops 14334581 ...


def parse_netapp_api_vf_stats(
    string_table: type_defs.StringTable,
) -> netapp_api.SectionSingleInstance:
    return netapp_api.parse_netapp_api_single_instance(string_table)


register.agent_section(
    name="netapp_api_vf_stats",
    parse_function=parse_netapp_api_vf_stats,
)


def discover_netapp_api_vf_stats(
    section_netapp_api_vf_stats: Optional[netapp_api.SectionSingleInstance],
    section_netapp_api_cpu: Optional[netapp_api.CPUSection],
) -> type_defs.DiscoveryResult:
    """
    >>> list(discover_netapp_api_vf_stats({'vfiler0': {}}, None))
    [Service(item='vfiler0')]
    >>> list(discover_netapp_api_vf_stats(
    ... {'vfiler0': {}},
    ... {'7mode': {'num_processors': '2', 'cpu_busy': '153993540928'}}))
    [Service(item='vfiler0')]
    """
    yield from discover_netapp_api_vf_stats_common(section_netapp_api_vf_stats or {})


def discover_netapp_api_vf_stats_common(
    section: netapp_api.SectionSingleInstance,
) -> type_defs.DiscoveryResult:
    """
    >>> list(discover_netapp_api_vf_stats_common({'vfiler0': {}}))
    [Service(item='vfiler0')]
    """
    yield from (Service(item=key) for key in section)


def check_netapp_api_vf_stats(
    item: str,
    params: Mapping[str, Any],
    section_netapp_api_vf_stats: Optional[netapp_api.SectionSingleInstance],
    section_netapp_api_cpu: Optional[netapp_api.CPUSection],
) -> type_defs.CheckResult:
    yield from _check_netapp_api_vf_stats(
        item,
        params,
        section_netapp_api_vf_stats,
        section_netapp_api_cpu,
        now=time.time(),
        value_store=get_value_store(),
    )


def _check_netapp_api_vf_stats(
    item: str,
    params: Mapping[str, Any],
    section_netapp_api_vf_stats: Optional[netapp_api.SectionSingleInstance],
    section_netapp_api_cpu: Optional[netapp_api.CPUSection],
    now: float,
    value_store: MutableMapping[str, Any],
) -> type_defs.CheckResult:

    vf = (section_netapp_api_vf_stats or {}).get(item)
    if not vf:
        return

    raise_ingore_res = False
    rates = {}

    for counter in ["cpu_busy", "cpu_busy_base"]:
        try:
            rates[counter] = get_rate(
                value_store,
                counter,
                now,
                int(vf["vfiler_%s" % counter]),
                raise_overflow=True,
            )
        except GetRateError:
            raise_ingore_res = True

    if raise_ingore_res:
        raise IgnoreResultsError("Initializing counters")

    # vFilers are 7mode only and cannot appear in clustermode
    num_processors = int((section_netapp_api_cpu or {}).get("7mode", {}).get("num_processors", 1))

    try:
        used_perc = (rates["cpu_busy"] / num_processors) / rates["cpu_busy_base"] * 100
        # Due to timing inaccuracies, the measured level can become > 100%. This makes users
        # unhappy, so cut it off.
        if used_perc < 0:
            used_perc = 0.0
        elif used_perc > 100:
            used_perc = 100.0
    except ZeroDivisionError:
        used_perc = 0.0

    yield from cpu_util.check_cpu_util(
        util=used_perc,
        params=params,
        value_store=value_store,
        this_time=now,
    )
    yield Result(state=state.OK, notice="Number of processors: %d" % num_processors)


register.check_plugin(
    name="netapp_api_vf_stats",
    sections=["netapp_api_vf_stats", "netapp_api_cpu"],
    service_name="CPU utilization %s",
    discovery_function=discover_netapp_api_vf_stats,
    check_function=check_netapp_api_vf_stats,
    check_default_parameters={"levels": (90.0, 95.0)},
    check_ruleset_name="cpu_utilization_multiitem",
)


def _render_ops(ops: float) -> str:
    return "%.2f/s" % ops


def check_netapp_api_vf_stats_traffic(
    item: str,
    section: netapp_api.SectionSingleInstance,
) -> type_defs.CheckResult:
    yield from _check_netapp_api_vf_stats_traffic(item, section, time.time(), get_value_store())


def _check_netapp_api_vf_stats_traffic(
    item: str,
    section: netapp_api.SectionSingleInstance,
    now: float,
    value_store: MutableMapping[str, Any],
) -> type_defs.CheckResult:
    vf = section.get(item)
    if not vf:
        return

    for entry, name, factor, render_func in [
        ("read_ops", "Read operations", 1, _render_ops),
        ("write_ops", "Write operations", 1, _render_ops),
        ("net_data_recv", "Received network data", 1024, render.iobandwidth),
        ("net_data_sent", "Sent network data", 1024, render.iobandwidth),
        ("read_bytes", "Read throughput", 1024, render.iobandwidth),
        ("write_bytes", "Write throughput", 1024, render.iobandwidth),
    ]:
        traffic = int(vf["vfiler_" + entry]) * factor
        try:
            ticks_per_sec = get_rate(
                value_store,
                entry,
                now,
                traffic,
            )
            yield from check_levels(
                ticks_per_sec,
                metric_name=entry,
                render_func=render_func,
                label=name,
            )
        except GetRateError:
            continue


register.check_plugin(
    name="netapp_api_vf_stats_traffic",
    sections=["netapp_api_vf_stats"],
    service_name="Traffic vFiler %s",
    discovery_function=discover_netapp_api_vf_stats_common,
    check_function=check_netapp_api_vf_stats_traffic,
)

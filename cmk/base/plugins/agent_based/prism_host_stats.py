#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>
# This is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
import time
from typing import Any, Dict, Mapping

from .agent_based_api.v1 import get_value_store, Metric, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.cpu_util import check_cpu_util
from .utils.memory import check_element

Section = Dict[str, Any]


def discovery_prism_host_stats(section: Section) -> DiscoveryResult:
    data = section.get("stats", {})
    if data.get("controller_avg_io_latency_usecs"):
        yield Service()


def check_prism_host_stats(section: Section) -> CheckResult:
    state = 0
    data = section.get("stats")
    if not data:
        return

    avg_latency = int(data.get("controller_avg_io_latency_usecs", 0))
    avg_read_lat = int(data.get("controller_avg_read_io_latency_usecs", 0))
    avg_write_lat = int(data.get("controller_avg_write_io_latency_usecs", 0))
    avg_read_bytes = int(data.get("controller_avg_read_io_size_kbytes", 0))
    avg_write_bytes = int(data.get("controller_avg_write_io_size_kbytes", 0))

    message = f"is {render.bytes(avg_read_bytes * 1000)} read and {render.bytes(avg_write_bytes * 1000)} write"
    yield Result(state=State(state), summary=message)
    yield Metric("avg_latency", avg_latency)
    yield Metric("avg_read_lat", avg_read_lat)
    yield Metric("avg_write_lat", avg_write_lat)
    yield Metric("avg_read_bytes", avg_read_bytes)
    yield Metric("avg_write_bytes", avg_write_bytes)


register.check_plugin(
    name="prism_host_stats",
    service_name="NTNX I/O",
    sections=["prism_host"],
    discovery_function=discovery_prism_host_stats,
    check_function=check_prism_host_stats,
)


def discovery_prism_host_stats_cpu(section: Section) -> DiscoveryResult:
    data = section.get("stats", {})
    if data.get("hypervisor_cpu_usage_ppm"):
        yield Service()


def check_prism_host_stats_cpu(params: Mapping[str, Any], section: Section) -> CheckResult:
    data = section.get("stats")
    if not data:
        return

    num_sockets = int(section.get("num_cpu_sockets", 0))
    num_cores = int(section.get("num_cpu_cores", 0))
    num_threads = int(section.get("num_cpu_threads", 0))
    hz_capacity = int(section.get("cpu_capacity_in_hz", 0))
    cpu_usage_perc = int(data.get("hypervisor_cpu_usage_ppm", 0)) / 10000.0

    yield from check_cpu_util(
        util=cpu_usage_perc,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )
    yield Result(
        state=State.OK,
        notice="%s/%s"
        % (
            render.frequency(hz_capacity / 100 * cpu_usage_perc),
            render.frequency(hz_capacity),
        ),
    )
    yield Result(
        state=State.OK,
        notice="Sockets: %d" % num_sockets,
    )
    yield Result(
        state=State.OK,
        notice="Cores/socket: %d" % int(num_cores / num_sockets),
    )
    yield Result(
        state=State.OK,
        notice="Threads: %d" % num_threads,
    )


register.check_plugin(
    name="prism_host_stats_cpu",
    service_name="NTNX CPU",
    sections=["prism_host"],
    check_default_parameters={},
    discovery_function=discovery_prism_host_stats_cpu,
    check_function=check_prism_host_stats_cpu,
    check_ruleset_name="prism_host_cpu",
)


def discovery_prism_host_stats_mem(section: Section) -> DiscoveryResult:
    data = section.get("stats", {})
    if data.get("hypervisor_memory_usage_ppm"):
        yield Service()


def check_prism_host_stats_mem(params: Mapping[str, Any], section: Section) -> CheckResult:
    data = section.get("stats")
    if not data:
        return

    mem_total = int(section.get("memory_capacity_in_bytes", 0))
    mem_usage = int(data.get("hypervisor_memory_usage_ppm", 0)) / 10000.0
    mem_usage_bytes = mem_total / 100 * mem_usage

    yield from check_element(
        "Usage",
        mem_usage_bytes,
        mem_total,
        ("perc_used", params["levels_upper"]),
        metric_name="mem_used",
    )
    yield Metric("mem_total", mem_total)


register.check_plugin(
    name="prism_host_stats_mem",
    service_name="NTNX Memory",
    sections=["prism_host"],
    check_default_parameters={
        "levels_upper": (80.0, 90.0),
    },
    discovery_function=discovery_prism_host_stats_mem,
    check_function=check_prism_host_stats_mem,
    check_ruleset_name="prism_host_mem",
)

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
from typing import Any, Dict, Mapping

from .agent_based_api.v1 import check_levels, Metric, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.memory import check_element

Section = Dict[str, Any]


def discovery_prism_vm_stats(section: Section) -> DiscoveryResult:
    data = section.get("stats", {})
    if data.get("controller_avg_io_latency_usecs"):
        yield Service()


def check_prism_vm_stats(section: Section) -> CheckResult:
    state = 0
    data = section.get("stats")
    if not data:
        return

    if section.get("powerState", "").lower() != "on":
        yield Result(state=State.OK, summary="VM not running no I/O check possible")
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
    yield Metric("avg_read_bytes", avg_read_bytes * 1000)
    yield Metric("avg_write_bytes", avg_write_bytes * 1000)


register.check_plugin(
    name="prism_vm_stats",
    service_name="NTNX I/O",
    sections=["prism_vm"],
    discovery_function=discovery_prism_vm_stats,
    check_function=check_prism_vm_stats,
)


def discovery_prism_vm_stats_cpu(section: Section) -> DiscoveryResult:
    data = section.get("stats", {})
    if data.get("hypervisor.cpu_ready_time_ppm"):
        yield Service()


def check_prism_vm_stats_cpu(params: Mapping[str, Any], section: Section) -> CheckResult:
    data = section.get("stats")
    if not data:
        return

    if section.get("powerState", "").lower() != "on":
        yield Result(state=State.OK, summary="VM not running no CPU check possible")
        return

    cpu_ready = int(data.get("hypervisor.cpu_ready_time_ppm", 0)) / 10000.0
    cpu_usage = int(data.get("hypervisor_cpu_usage_ppm", 0)) / 10000.0

    yield from check_levels(
        value=cpu_usage,
        metric_name="cpu_usage",
        levels_upper=params.get("levels", (None, None)),
        render_func=render.percent,
        label="CPU usage",
        boundaries=(0, 100),
    )
    yield from check_levels(
        value=cpu_ready,
        metric_name="cpu_ready",
        levels_upper=params.get("levels_rdy", (None, None)),
        render_func=render.percent,
        label="CPU ready",
        boundaries=(0, 100),
    )


register.check_plugin(
    name="prism_vm_stats_cpu",
    service_name="NTNX CPU",
    sections=["prism_vm"],
    check_default_parameters={"levels": (80.0, 90.0), "levels_rdy": (5.0, 10.0)},
    discovery_function=discovery_prism_vm_stats_cpu,
    check_function=check_prism_vm_stats_cpu,
    check_ruleset_name="prism_vm_cpu",
)


def discovery_prism_vm_stats_mem(section: Section) -> DiscoveryResult:
    data = section.get("stats", {})
    if data.get("guest.memory_usage_ppm"):
        yield Service()


def check_prism_vm_stats_mem(params: Mapping[str, Any], section: Section) -> CheckResult:
    data = section.get("stats")
    if not data:
        return

    if section.get("powerState", "").lower() != "on":
        yield Result(state=State.OK, summary="VM not running no memory check possible")
        return

    mem_usage_bytes = int(data.get("guest.memory_usage_bytes", 0))
    if mem_usage_bytes != 0:
        mem_usage = int(data.get("guest.memory_usage_ppm", 0)) / 10000.0
        mem_total = int(mem_usage_bytes / mem_usage * 100)
        if mem_total < 500000000:
            mem_total = mem_total * 1024
            mem_usage_bytes = mem_usage_bytes * 1024

        yield from check_element(
            "Usage",
            mem_usage_bytes,
            mem_total,
            ("perc_used", params["levels_upper"]),
            metric_name="mem_used",
        )
        yield Metric("mem_total", mem_total)


register.check_plugin(
    name="prism_vm_stats_mem",
    service_name="NTNX Memory",
    sections=["prism_vm"],
    check_default_parameters={
        "levels_upper": (80.0, 90.0),
    },
    discovery_function=discovery_prism_vm_stats_mem,
    check_function=check_prism_vm_stats_mem,
    check_ruleset_name="prism_vm_memory",
)

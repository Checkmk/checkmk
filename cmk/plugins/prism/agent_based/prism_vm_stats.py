#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.lib.memory import check_element

Section = Mapping[str, Any]


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


check_plugin_prism_vm_stats = CheckPlugin(
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

    yield from check_levels_v1(
        value=cpu_usage,
        metric_name="cpu_usage",
        levels_upper=params.get("levels", (None, None)),
        render_func=render.percent,
        label="CPU usage",
        boundaries=(0, 100),
    )
    yield from check_levels_v1(
        value=cpu_ready,
        metric_name="cpu_ready",
        levels_upper=params.get("levels_rdy", (None, None)),
        render_func=render.percent,
        label="CPU ready",
        boundaries=(0, 100),
    )


check_plugin_prism_vm_stats_cpu = CheckPlugin(
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
    if mem_usage_bytes == 0:
        yield Result(state=State.OK, summary="No memory usage data available")
        return

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


check_plugin_prism_vm_stats_mem = CheckPlugin(
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

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Iterable, Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.jolokia.agent_based.lib import (
    jolokia_mbean_attribute,
    parse_jolokia_json_output,
)

Section = Mapping[str, Mapping[str, Any]]


def parse_jolokia_jvm_memory(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, dict[str, object]]] = {}
    for instance, mbean, data in parse_jolokia_json_output(string_table):
        type_ = jolokia_mbean_attribute("type", mbean)
        parsed_data = parsed.setdefault(instance, {}).setdefault(type_, {})
        parsed_data.update(data)

    return parsed


def _jolokia_check_abs_and_perc(
    mem_type: str, value: float, value_max: float | None, params: Mapping[str, Any]
) -> CheckResult:
    perf_name = ("mem_%s" % mem_type) if mem_type != "total" else None

    yield from check_levels(
        value,
        perf_name,
        params.get("abs_%s" % mem_type),
        infoname=mem_type.title(),
        human_readable_func=render.bytes,
        boundaries=(None, value_max),
    )

    if value_max is None:
        return

    perc_val = float(value) / float(value_max) * 100.0
    yield from check_levels(
        perc_val,
        None,
        params.get("perc_%s" % mem_type),
        human_readable_func=render.percent,
        boundaries=(0, 100),
    )


def discover_jolokia_jvm_memory(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item, data in section.items() if data.get("Memory"))


def _iter_type_value_max(mem_data: Mapping[str, Any]) -> Iterable[tuple[str, float, float | None]]:
    heap_data = mem_data.get("HeapMemoryUsage", {})
    nonheap_data = mem_data.get("NonHeapMemoryUsage", {})
    heap = heap_data.get("used")
    nonheap = nonheap_data.get("used")
    heapmax = heap_data.get("max", -1)
    nonheapmax = nonheap_data.get("max", -1)

    totalmax = heapmax + nonheapmax
    if heapmax <= 0:
        heapmax = None
        totalmax = None
    if nonheapmax <= 0:
        nonheapmax = None
        totalmax = None

    if heap is not None:
        yield "heap", heap, heapmax
    if nonheap is not None:
        yield "nonheap", nonheap, nonheapmax
    if heap is not None and nonheap is not None:
        yield "total", heap + nonheap, totalmax


def check_jolokia_jvm_memory(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (instance_data := section.get(item)):
        return
    mem_data = instance_data.get("Memory", {})

    for mem_type, value, value_max in _iter_type_value_max(mem_data):
        yield from _jolokia_check_abs_and_perc(mem_type, value, value_max, params)


agent_section_jolokia_jvm_memory = AgentSection(
    name="jolokia_jvm_memory",
    parse_function=parse_jolokia_jvm_memory,
)


check_plugin_jolokia_jvm_memory = CheckPlugin(
    name="jolokia_jvm_memory",
    service_name="JVM %s Memory",
    discovery_function=discover_jolokia_jvm_memory,
    check_function=check_jolokia_jvm_memory,
    check_ruleset_name="jvm_memory",
    check_default_parameters={
        "perc_heap": (80.0, 90.0),
        "perc_nonheap": (80.0, 90.0),
        "perc_total": (80.0, 90.0),
    },
)

# .
#   .--Memory Pools--------------------------------------------------------.
#   |   __  __                                   ____             _        |
#   |  |  \/  | ___ _ __ ___   ___  _ __ _   _  |  _ \ ___   ___ | |___    |
#   |  | |\/| |/ _ \ '_ ` _ \ / _ \| '__| | | | | |_) / _ \ / _ \| / __|   |
#   |  | |  | |  __/ | | | | | (_) | |  | |_| | |  __/ (_) | (_) | \__ \   |
#   |  |_|  |_|\___|_| |_| |_|\___/|_|   \__, | |_|   \___/ \___/|_|___/   |
#   |                                    |___/                             |
#   '----------------------------------------------------------------------'


def discover_jolokia_jvm_memory_pools(section: Section) -> DiscoveryResult:
    for instance, instance_info in section.items():
        for data in instance_info.get("MemoryPool", {}).values():
            pool = data.get("Name")
            if pool:
                yield Service(item=f"{instance} Memory Pool {pool}")


def _get_jolokia_jvm_mempool_data(item: str, section: Section) -> Mapping[str, Any]:
    instance, pool_name = item.split(" Memory Pool ", 1)
    data = section.get(instance, {}).get("MemoryPool", {})
    pools = [pool for pool in data.values() if pool.get("Name") == pool_name]
    return pools[0] if pools else {}


def check_jolokia_jvm_memory_pools(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    data = _get_jolokia_jvm_mempool_data(item, section)
    if not (usage := data.get("Usage")):
        return

    if isinstance(usage, str) and usage.startswith("ERROR"):
        yield Result(
            state=State.UNKNOWN,
            summary="Check received invalid data. See long output for details.",
            details=(
                f'Error was: "{usage}". '
                "This could be a support case for the Jolokia API maintainers: "
                "https://github.com/rhuss/jolokia"
            ),
        )
        return

    value_max = usage.get("max", -1)
    value_max = value_max if value_max > 0 else None
    yield from _jolokia_check_abs_and_perc("used", usage["used"], value_max, params)

    init = usage.get("init")
    if init is not None:
        yield Result(state=State.OK, summary="Initially: %s" % render.bytes(init))

    committed = usage.get("committed")
    if committed is not None:
        yield Result(state=State.OK, summary="Committed: %s" % render.bytes(committed))


check_plugin_jolokia_jvm_memory_pools = CheckPlugin(
    name="jolokia_jvm_memory_pools",
    service_name="JVM %s",
    sections=["jolokia_jvm_memory"],
    discovery_function=discover_jolokia_jvm_memory_pools,
    check_function=check_jolokia_jvm_memory_pools,
    check_ruleset_name="jvm_memory_pools",
    check_default_parameters={
        "perc_used": (80.0, 90.0),
    },
)

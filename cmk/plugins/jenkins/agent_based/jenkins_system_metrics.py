#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections.abc import Callable, Mapping
from contextlib import suppress
from typing import Any, Literal

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    render,
    Service,
    StringTable,
)

from .lib import render_integer

Section = Mapping[str, Mapping[str, Any]]
MetricsItems = Literal["HTTP Requests", "Memory", "Threads"]

PREFIX_DESCRIPTIONS = {
    "vm.memory.total": "JVM memory",
    "vm.memory.heap": "JVM memory: heap",
    "vm.memory.non-heap": "JVM memory: non-heap",
}

SUFFIX_DESCRIPTIONS = {
    "usage": "usage",
    "used": "used",
    "committed": "available by OS",
    "max": "max. allowed",
    "init": "initially requested",
    "used-after-gc": "used after GC",
}


def parse_jenkins_system_metrics(string_table: StringTable) -> Section:
    """
    Parse metrics retrieved from Jenkins in JSON format.
    """
    parsed: dict[str, Any] = {}

    for line in string_table:
        parsed.update(json.loads(line[0]))

    return parsed


def discover_jenkins_metrics_service(section: Section) -> DiscoveryResult:
    yield Service(item="HTTP Requests")
    yield Service(item="Memory")
    yield Service(item="Threads")


def check_jenkins_metrics(
    item: MetricsItems,
    params: Mapping[str, FixedLevelsT],
    section: Section,
) -> CheckResult:
    if not section:
        return

    match item:
        case "HTTP Requests":
            counters = section["counters"]
            counter_metrics = (("http.activeRequests", "HTTP requests: active"),)
            for counter_identifier, counter_description in counter_metrics:
                metric_name = sanitize_metrics_identifier(
                    f"jenkins_metrics_counter_{counter_identifier}"
                )
                yield from check_levels(
                    counters[counter_identifier]["count"],
                    metric_name=metric_name,
                    levels_upper=params.get(metric_name),
                    render_func=render_integer,
                    label=counter_description,
                )
        case "Memory":
            # The metrics dict groups metrics by type, so we have to address this.
            gauges = section["gauges"]
            # Memory metrics aren't all predictable, because their name is depending
            # on the used JVM and the selected GC.
            for key, value_container in gauges.items():
                if not key.startswith("vm.memory."):
                    continue

                # Limit the displayed metrics to avoid cluttering:
                if is_undesired_memory_pool(key):
                    continue

                memory_value = value_container["value"]

                if memory_value == -1:
                    # Unspecified value - nothing to show here
                    continue

                metric_name = sanitize_metrics_identifier(f"jenkins_memory_{key}")

                render_func: Callable[[float], str] = render.bytes
                if key.endswith(".usage"):
                    # .usage indicates a percentage
                    render_func = render.percent
                    memory_value *= 100

                yield from check_levels(
                    memory_value,
                    metric_name=metric_name,
                    levels_upper=params.get(metric_name),
                    render_func=render_func,
                    label=get_memory_metric_description(key),
                    notice_only=not key.endswith(".used"),
                )

        case "Threads":
            # The metrics dict groups metrics by type, so we have to address this.
            gauges = section["gauges"]
            thread_metrics = (
                ("vm.count", "Total threads"),
                ("vm.blocked.count", "Blocked threads"),
                ("vm.runnable.count", "Active threads"),
                ("vm.new.count", "Unstarted threads"),
                ("vm.deadlock.count", "Deadlocked threads"),
                ("vm.daemon.count", "Daemon threads"),
                ("vm.waiting.count", "Waiting threads"),
                ("vm.timed_waiting.count", "Timed waiting threads"),
                ("vm.terminated.count", "Terminated threads"),
            )
            for key, description in thread_metrics:
                if (metric_value_container := gauges.get(key)) is None:
                    continue

                metric_value = metric_value_container["value"]

                metric_name = sanitize_metrics_identifier(f"jenkins_threads_{key}")
                yield from check_levels(
                    metric_value,
                    metric_name=metric_name,
                    levels_upper=params.get(metric_name),
                    render_func=render_integer,
                    label=description,
                )
        case _:
            raise RuntimeError(f"Received unexpected item: {item!r}")


def sanitize_metrics_identifier(identifier: str) -> str:
    # We want to strip special characters from the identifier.
    # Known inclusions: . _
    return identifier.replace(".", "_").replace("'", "_").replace("-", "_").lower()


def get_memory_metric_description(identifier: str) -> str:
    "Get a description for the given metric"
    # For detailed descriptions see https://plugins.jenkins.io/metrics/

    prefix, metrics_type = identifier.rsplit(".", maxsplit=1)

    # Try to generate a good description by using what we know about prefix and suffix of our metric identifier.
    with suppress(KeyError):
        return f"{PREFIX_DESCRIPTIONS[prefix]}: {SUFFIX_DESCRIPTIONS[metrics_type]}"

    if prefix.startswith("vm.memory.pools."):
        *_, pool_name = prefix.split(".", maxsplit=3)
        return f"JVM memory pool {pool_name}: {SUFFIX_DESCRIPTIONS[metrics_type]}"

    # Fallback if we do not have a better description
    return identifier


def is_undesired_memory_pool(identifier: str) -> bool:
    return identifier.startswith("vm.memory.pools.") and (
        "CodeHeap-" in identifier or "Compressed-Class-Space" in identifier
    )


agent_section_jenkins_metrics = AgentSection(
    name="jenkins_system_metrics",
    parse_function=parse_jenkins_system_metrics,
)

check_plugin_jenkins_metrics = CheckPlugin(
    name="jenkins_system_metrics",
    service_name="Jenkins %s",
    discovery_function=discover_jenkins_metrics_service,
    check_function=check_jenkins_metrics,
    check_default_parameters={},
    check_ruleset_name="jenkins_system_metrics",
)

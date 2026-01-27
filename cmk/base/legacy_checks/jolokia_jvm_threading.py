#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import (
    check_levels,
    LegacyCheckDefinition,
    LegacyCheckResult,
    LegacyDiscoveryResult,
)
from cmk.agent_based.v2 import get_rate, get_value_store, StringTable
from cmk.plugins.jolokia.agent_based.lib import (
    jolokia_mbean_attribute,
    parse_jolokia_json_output,
)

check_info = {}

Section = Mapping[str, Any]


def parse_jolokia_jvm_threading(string_table: StringTable) -> Section:
    parsed = {}
    for instance, mbean, data in parse_jolokia_json_output(string_table):
        type_ = jolokia_mbean_attribute("type", mbean)
        parsed_data = parsed.setdefault(instance, {}).setdefault(type_, {})

        if type_ == "ThreadPool":
            for key in data:
                name = jolokia_mbean_attribute("name", key).strip('"')
                parsed_data[name] = data[key]
        else:
            parsed_data.update(data)

    return parsed


def discover_jolokia_jvm_threading(section: Section) -> LegacyDiscoveryResult:
    yield from ((instance, {}) for instance, data in section.items() if data.get("Threading"))


def check_jolokia_jvm_threading(
    item: str, params: Mapping[str, object], section: Section
) -> LegacyCheckResult:
    if not (instance_data := section.get(item)):
        return
    data = instance_data.get("Threading", {})
    count = data.get("ThreadCount")
    if count is not None:
        levels = params.get("threadcount_levels")
        yield check_levels(
            count, "ThreadCount", levels, infoname="Count", human_readable_func=lambda i: "%.f" % i
        )

        counter = "jolokia_jvm_threading.count.%s" % item
        thread_rate = get_rate(get_value_store(), counter, time.time(), count)
        levels = params.get("threadrate_levels")
        yield check_levels(thread_rate, "ThreadRate", levels, infoname="Rate")

    for key, name in (
        ("DaemonThreadCount", "Daemon threads"),
        ("PeakThreadCount", "Peak count"),
        ("TotalStartedThreadCount", "Total started"),
    ):
        value = data.get(key)
        if value is None:
            continue
        levels = params.get("%s_levels" % key.lower())
        yield check_levels(
            value, key, levels, infoname=name, human_readable_func=lambda i: "%.f" % i
        )


check_info["jolokia_jvm_threading"] = LegacyCheckDefinition(
    name="jolokia_jvm_threading",
    parse_function=parse_jolokia_jvm_threading,
    service_name="JVM %s Threading",
    discovery_function=discover_jolokia_jvm_threading,
    check_function=check_jolokia_jvm_threading,
    check_ruleset_name="jvm_threading",
)


def discover_jolokia_jvm_threading_pool(section: Section) -> LegacyDiscoveryResult:
    for instance, instance_data in section.items():
        threadpool_data = instance_data.get("ThreadPool", {})
        for name in threadpool_data:
            yield f"{instance} ThreadPool {name}", {}


def check_jolokia_jvm_threading_pool(
    item: str,
    params: dict[str, tuple[str, tuple[int, int]]],
    section: Section,
) -> LegacyCheckResult:
    instance, pool_name = item.split(" ThreadPool ", 1)
    thread_pools = section.get(instance, {}).get("ThreadPool", {})
    threadpool_info = thread_pools.get(pool_name, {})
    max_threads = threadpool_info.get("maxThreads")
    if max_threads is None:
        return

    if max_threads == -1:
        yield 0, "Maximum threads: not set (unlimited)"
        return

    yield 0, "Maximum threads: %d" % max_threads

    for key, name in (
        ("currentThreadsBusy", "Busy"),
        ("currentThreadCount", "Total"),
    ):
        value = threadpool_info.get(key)
        if value is None:
            continue

        levels_type, (warn, crit) = params.get(key, (None, (None, None)))
        if warn is not None and levels_type == "percentage":
            warn = max_threads * warn / 100.0
            crit = max_threads * crit / 100.0

        yield check_levels(
            value,
            key,
            (warn, crit),
            boundaries=(None, max_threads),
            infoname=name,
            human_readable_func=lambda f: "%.f" % f,
        )


check_info["jolokia_jvm_threading.pool"] = LegacyCheckDefinition(
    name="jolokia_jvm_threading_pool",
    service_name="JVM %s",
    sections=["jolokia_jvm_threading"],
    discovery_function=discover_jolokia_jvm_threading_pool,
    check_function=check_jolokia_jvm_threading_pool,
    check_ruleset_name="jvm_tp",
    check_default_parameters={
        "currentThreadsBusy": ("percentage", (80, 90)),
    },
)

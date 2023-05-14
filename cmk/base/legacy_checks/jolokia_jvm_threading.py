#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

import time

from cmk.base.check_api import (
    check_levels,
    discover,
    get_parsed_item_data,
    get_rate,
    LegacyCheckDefinition,
)
from cmk.base.check_legacy_includes.jolokia import (
    jolokia_mbean_attribute,
    parse_jolokia_json_output,
)
from cmk.base.config import check_info, factory_settings

factory_settings["jolokia_jvm_threading.pool"] = {
    "currentThreadsBusy": (80, 90),
}


def parse_jolokia_jvm_threading(info):
    parsed = {}
    for instance, mbean, data in parse_jolokia_json_output(info):
        type_ = jolokia_mbean_attribute("type", mbean)
        parsed_data = parsed.setdefault(instance, {}).setdefault(type_, {})

        if type_ == "ThreadPool":
            for key in data:
                name = jolokia_mbean_attribute("name", key).strip('"')
                parsed_data[name] = data[key]
        else:
            parsed_data.update(data)

    return parsed


@discover
def discover_jolokia_jvm_threading(_instance, data):
    return bool(data.get("Threading"))


@get_parsed_item_data
def check_jolokia_jvm_threading(item, params, instance_data):
    data = instance_data.get("Threading", {})
    count = data.get("ThreadCount")
    if count is not None:
        levels = params.get("threadcount_levels")
        yield check_levels(
            count, "ThreadCount", levels, infoname="Count", human_readable_func=lambda i: "%.f" % i
        )

        counter = "jolokia_jvm_threading.count.%s" % item
        thread_rate = get_rate(counter, time.time(), count, allow_negative=True)
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
    parse_function=parse_jolokia_jvm_threading,
    discovery_function=discover_jolokia_jvm_threading,
    check_function=check_jolokia_jvm_threading,
    service_name="JVM %s Threading",
    check_ruleset_name="jvm_threading",
)


def discover_jolokia_jvm_threading_pool(parsed):
    for instance in parsed:
        threadpool_data = parsed[instance].get("ThreadPool", {})
        for name in threadpool_data:
            yield "%s ThreadPool %s" % (instance, name), {}


def check_jolokia_jvm_threading_pool(item, params, parsed):
    instance, pool_name = item.split(" ThreadPool ", 1)
    thread_pools = parsed.get(instance, {}).get("ThreadPool", {})
    threadpool_info = thread_pools.get(pool_name, {})
    max_threads = threadpool_info.get("maxThreads")
    if max_threads is None:
        return

    yield 0, "Maximum threads: %d" % max_threads

    for key, name in (
        ("currentThreadsBusy", "Busy"),
        ("currentThreadCount", "Total"),
    ):
        value = threadpool_info.get(key)
        if value is None:
            continue
        warn, crit = params.get(key, (None, None))
        if warn is not None:
            warn *= max_threads / 100.0
            crit *= max_threads / 100.0

        yield check_levels(
            value,
            key,
            (warn, crit),
            boundaries=(None, max_threads),
            infoname=name,
            human_readable_func=lambda f: "%.f" % f,
        )


check_info["jolokia_jvm_threading.pool"] = LegacyCheckDefinition(
    discovery_function=discover_jolokia_jvm_threading_pool,
    check_function=check_jolokia_jvm_threading_pool,
    default_levels_variable="jolokia_jvm_threading.pool",
    service_name="JVM %s",
    check_ruleset_name="jvm_tp",
)

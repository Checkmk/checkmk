#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.check_legacy_includes.mem import check_memory_element, MEMORY_DEFAULT_LEVELS
from cmk.plugins.lib.couchbase import parse_couchbase_lines

check_info = {}


def discover_couchbase_nodes_stats(section):
    yield from ((item, {}) for item in section)


check_info["couchbase_nodes_stats"] = LegacyCheckDefinition(
    name="couchbase_nodes_stats",
    parse_function=parse_couchbase_lines,
    discovery_function=discover_couchbase_nodes_stats,
)


def check_couchbase_nodes_cpu_util(item, params, parsed):
    if not (data := parsed.get(item)):
        return

    try:
        yield from check_cpu_util(float(data["cpu_utilization_rate"]), params)
    except (ValueError, KeyError):
        return


def discover_couchbase_nodes_stats_cpu_util(section):
    yield from ((item, {}) for item in section)


check_info["couchbase_nodes_stats.cpu_util"] = LegacyCheckDefinition(
    name="couchbase_nodes_stats_cpu_util",
    service_name="Couchbase %s CPU utilization",
    sections=["couchbase_nodes_stats"],
    discovery_function=discover_couchbase_nodes_stats_cpu_util,
    check_function=check_couchbase_nodes_cpu_util,
    check_ruleset_name="cpu_utilization_multiitem",
)


def check_couchbase_nodes_mem(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    try:
        mem_total = data["mem_total"]
        mem_free = data["mem_free"]
        swap_total = data["swap_total"]
        swap_used = data["swap_used"]
    except KeyError:
        return

    warn_ram, crit_ram = params.get("levels", (None, None))
    mode_ram = "abs_used" if isinstance(warn_ram, int) else "perc_used"

    yield check_memory_element(
        "RAM",
        mem_total - mem_free,
        mem_total,
        (mode_ram, (warn_ram, crit_ram)),
        metric_name="mem_used",
    )

    yield check_memory_element(
        "Swap",
        swap_used,
        swap_total,
        None,
        metric_name="swap_used",
    )


def discover_couchbase_nodes_stats_mem(section):
    yield from ((item, {}) for item in section)


check_info["couchbase_nodes_stats.mem"] = LegacyCheckDefinition(
    name="couchbase_nodes_stats_mem",
    service_name="Couchbase %s Memory",
    sections=["couchbase_nodes_stats"],
    discovery_function=discover_couchbase_nodes_stats_mem,
    check_function=check_couchbase_nodes_mem,
    check_ruleset_name="memory_multiitem",
    check_default_parameters=MEMORY_DEFAULT_LEVELS,
)

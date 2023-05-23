#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover, LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.check_legacy_includes.mem import check_memory_element, MEMORY_DEFAULT_LEVELS
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.utils.couchbase import parse_couchbase_lines

check_info["couchbase_nodes_stats"] = LegacyCheckDefinition(
    parse_function=parse_couchbase_lines,
)


def check_couchbase_nodes_cpu_util(item, params, parsed):
    if not (data := parsed.get(item)):
        return

    try:
        yield from check_cpu_util(float(data["cpu_utilization_rate"]), params)
    except (ValueError, KeyError):
        return


check_info["couchbase_nodes_stats.cpu_util"] = LegacyCheckDefinition(
    discovery_function=discover(),
    check_function=check_couchbase_nodes_cpu_util,
    service_name="Couchbase %s CPU utilization",
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


check_info["couchbase_nodes_stats.mem"] = LegacyCheckDefinition(
    discovery_function=discover(),
    check_function=check_couchbase_nodes_mem,
    service_name="Couchbase %s Memory",
    check_ruleset_name="memory_multiitem",
    check_default_parameters=MEMORY_DEFAULT_LEVELS,
)

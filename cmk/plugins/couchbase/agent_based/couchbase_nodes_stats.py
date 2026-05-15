#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping
from typing import Any, Literal

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines, Section
from cmk.plugins.lib.cpu_util import check_cpu_util
from cmk.plugins.lib.memory import check_element

_MEMORY_DEFAULT_LEVELS: Mapping[str, Any] = {"levels": (150.0, 200.0)}


def discover_couchbase_nodes_stats(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_couchbase_nodes_cpu_util(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    try:
        util = float(data["cpu_utilization_rate"])
    except (ValueError, KeyError):
        return
    yield from check_cpu_util(
        util=util,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


def check_couchbase_nodes_mem(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    try:
        mem_total = data["mem_total"]
        mem_free = data["mem_free"]
        swap_total = data["swap_total"]
        swap_used = data["swap_used"]
    except KeyError:
        return

    warn_ram, crit_ram = params.get("levels", (None, None))
    mode: Literal["abs_used", "perc_used"] = (
        "abs_used" if isinstance(warn_ram, int) else "perc_used"
    )

    yield from check_element(
        "RAM",
        mem_total - mem_free,
        mem_total,
        (mode, (warn_ram, crit_ram)),
        metric_name="mem_used",
    )

    yield from check_element(
        "Swap",
        swap_used,
        swap_total,
        None,
        metric_name="swap_used",
    )


agent_section_couchbase_nodes_stats = AgentSection(
    name="couchbase_nodes_stats",
    parse_function=parse_couchbase_lines,
)


check_plugin_couchbase_nodes_stats_cpu_util = CheckPlugin(
    name="couchbase_nodes_stats_cpu_util",
    service_name="Couchbase %s CPU utilization",
    sections=["couchbase_nodes_stats"],
    discovery_function=discover_couchbase_nodes_stats,
    check_function=check_couchbase_nodes_cpu_util,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={},
)


check_plugin_couchbase_nodes_stats_mem = CheckPlugin(
    name="couchbase_nodes_stats_mem",
    service_name="Couchbase %s Memory",
    sections=["couchbase_nodes_stats"],
    discovery_function=discover_couchbase_nodes_stats,
    check_function=check_couchbase_nodes_mem,
    check_ruleset_name="memory_multiitem",
    check_default_parameters=_MEMORY_DEFAULT_LEVELS,
)

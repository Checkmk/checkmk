#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ported by (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, render, Service

Section = Mapping[str, Mapping[str, Any]]


def discovery_prism_cluster_mem(section: Section) -> DiscoveryResult:
    if "hypervisor_memory_usage_ppm" in section.get("stats", {}):
        yield Service()


def check_prism_cluster_mem(params: Mapping[str, Any], section: Section) -> CheckResult:
    mem_used = section.get("stats", {}).get("hypervisor_memory_usage_ppm")
    if mem_used is None:
        return

    mem_usage = int(mem_used) / 10000

    yield from check_levels_v1(
        mem_usage,
        metric_name="prism_cluster_mem_used",
        levels_upper=params["levels"],
        boundaries=(0.0, 100.0),
        render_func=render.percent,
        label="Total Memory Usage",
    )


check_plugin_prism_cluster_mem = CheckPlugin(
    name="prism_cluster_mem",
    service_name="NTNX Cluster Memory",
    sections=["prism_info"],
    discovery_function=discovery_prism_cluster_mem,
    check_function=check_prism_cluster_mem,
    check_default_parameters={"levels": (70.0, 80.0)},
    check_ruleset_name="prism_cluster_mem",
)

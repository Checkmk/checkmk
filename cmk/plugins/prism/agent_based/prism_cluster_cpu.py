#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ported by (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>
import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, get_value_store, Service
from cmk.plugins.lib.cpu_util import check_cpu_util

Section = Mapping[str, Mapping[str, Any]]


def discovery_prism_cluster_cpu(section: Section) -> DiscoveryResult:
    if "hypervisor_cpu_usage_ppm" in section.get("stats", {}):
        yield Service()


def check_prism_cluster_cpu(params: Mapping[str, Any], section: Section) -> CheckResult:
    cpu_used = section.get("stats", {}).get("hypervisor_cpu_usage_ppm")
    if cpu_used is None:
        return

    cpu_usage = int(cpu_used) / 10000

    yield from check_cpu_util(
        util=cpu_usage,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


check_plugin_prism_cluster_cpu = CheckPlugin(
    name="prism_cluster_cpu",
    service_name="NTNX Cluster CPU",
    sections=["prism_info"],
    discovery_function=discovery_prism_cluster_cpu,
    check_function=check_prism_cluster_cpu,
    check_default_parameters={},
    check_ruleset_name="prism_cluster_cpu",
)

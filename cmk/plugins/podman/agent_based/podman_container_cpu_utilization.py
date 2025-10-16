#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping, MutableMapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
)
from cmk.plugins.lib.cpu_util import check_cpu_util

from .lib import SectionPodmanContainerStats


def discover_podman_container_cpu_utilization(
    section: SectionPodmanContainerStats,
) -> DiscoveryResult:
    yield Service()


def check_podman_container_cpu_utilization(
    params: Mapping[str, object], section: SectionPodmanContainerStats
) -> CheckResult:
    yield from _check_cpu_utilization_testable(
        util=section.cpu_util,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


def _check_cpu_utilization_testable(
    util: float,
    params: Mapping[str, object],
    value_store: MutableMapping[str, object],
    this_time: float,
) -> CheckResult:
    yield from check_cpu_util(
        util=util,
        params=params,
        value_store=value_store,
        this_time=this_time,
    )


check_plugin_podman_container_cpu_utilization = CheckPlugin(
    name="podman_container_cpu_utilization",
    service_name="CPU utilization",
    sections=["podman_container_stats"],
    discovery_function=discover_podman_container_cpu_utilization,
    check_function=check_podman_container_cpu_utilization,
    check_ruleset_name="cpu_utilization_os",
    check_default_parameters={
        "util": (70.0, 80.0),
    },
)

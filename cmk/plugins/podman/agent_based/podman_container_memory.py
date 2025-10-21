#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
)
from cmk.plugins.collection.agent_based.mem_used import check_mem_used
from cmk.plugins.lib.memory import SectionMemUsed

from .lib import SectionPodmanContainerStats


def discover_podman_container_memory(
    section: SectionPodmanContainerStats,
) -> DiscoveryResult:
    yield Service()


def check_podman_container_memory(
    params: Mapping[str, tuple[float, float] | int], section: SectionPodmanContainerStats
) -> CheckResult:
    yield from check_mem_used(
        params=params,
        section=SectionMemUsed(
            MemFree=section.mem_total - section.mem_used,
            MemTotal=section.mem_total,
        ),
    )


check_plugin_podman_container_memory = CheckPlugin(
    name="podman_container_memory",
    service_name="Memory",
    sections=["podman_container_stats"],
    discovery_function=discover_podman_container_memory,
    check_function=check_podman_container_memory,
    check_ruleset_name="memory",
    check_default_parameters={
        "levels": (150.0, 200.0),
    },
)

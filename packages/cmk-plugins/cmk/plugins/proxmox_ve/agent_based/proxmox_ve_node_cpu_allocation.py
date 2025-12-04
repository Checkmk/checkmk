#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Literal

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    NoLevelsT,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.proxmox_ve.lib.node_allocation import SectionNodeAllocation

type Params = Mapping[
    Literal["cpu_allocation_ratio"],
    NoLevelsT | FixedLevelsT[float],
]


def discover_proxmox_ve_node_cpu_allocation(section: SectionNodeAllocation) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_node_cpu_allocation(
    params: Params, section: SectionNodeAllocation
) -> CheckResult:
    yield from check_levels(
        value=(section.allocated_cpu / section.node_total_cpu) * 100,
        levels_upper=params["cpu_allocation_ratio"],
        label="CPU allocation ratio",
        metric_name="node_cpu_allocation_ratio",
        render_func=render.percent,
    )

    yield Result(state=State.OK, summary=f"Allocated CPUs: {int(section.allocated_cpu)}")


check_plugin_proxmox_ve_node_cpu_allocation = CheckPlugin(
    name="proxmox_ve_node_cpu_allocation",
    sections=["proxmox_ve_node_allocation"],
    service_name="Proxmox VE CPU allocation ratio",
    discovery_function=discover_proxmox_ve_node_cpu_allocation,
    check_function=check_proxmox_ve_node_cpu_allocation,
    check_ruleset_name="proxmox_ve_node_cpu_allocation",
    check_default_parameters={
        "cpu_allocation_ratio": ("fixed", (150.0, 200.0)),
    },
)

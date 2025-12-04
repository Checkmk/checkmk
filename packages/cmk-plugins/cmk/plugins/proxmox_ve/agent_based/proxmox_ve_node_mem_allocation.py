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
    Literal["mem_allocation_ratio"],
    NoLevelsT | FixedLevelsT[float],
]


def discover_proxmox_ve_node_mem_allocation(section: SectionNodeAllocation) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_node_mem_allocation(
    params: Params, section: SectionNodeAllocation
) -> CheckResult:
    yield from check_levels(
        value=(section.allocated_mem / section.node_total_mem) * 100,
        levels_upper=params["mem_allocation_ratio"],
        label="Memory allocation ratio",
        metric_name="node_mem_allocation_ratio",
        render_func=render.percent,
    )

    yield Result(state=State.OK, summary=f"Allocated Memory: {render.bytes(section.allocated_mem)}")


check_plugin_proxmox_ve_node_mem_allocation = CheckPlugin(
    name="proxmox_ve_node_mem_allocation",
    sections=["proxmox_ve_node_allocation"],
    service_name="Proxmox VE Memory allocation ratio",
    discovery_function=discover_proxmox_ve_node_mem_allocation,
    check_function=check_proxmox_ve_node_mem_allocation,
    check_ruleset_name="proxmox_ve_node_mem_allocation",
    check_default_parameters={
        "mem_allocation_ratio": ("fixed", (100.0, 120.0)),
    },
)

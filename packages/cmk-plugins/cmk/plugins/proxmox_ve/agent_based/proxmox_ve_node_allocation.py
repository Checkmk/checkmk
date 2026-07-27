#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

from pydantic import BaseModel

from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.proxmox_ve.lib.node_allocation import SectionNodeAllocation


class _RawRunningVM(BaseModel, frozen=True):
    maxcpu: float
    maxmem: float


class _RawNodeAllocation(BaseModel, frozen=True):
    status: str
    node_total_cpu: float | None
    node_total_mem: float | None
    running_vms: Sequence[_RawRunningVM]


def _pre_parse_proxmox_ve_node_allocation(string_table: StringTable) -> _RawNodeAllocation:
    return _RawNodeAllocation.model_validate_json(string_table[0][0])


def parse_proxmox_ve_node_allocation(string_table: StringTable) -> SectionNodeAllocation:
    raw_node = _pre_parse_proxmox_ve_node_allocation(string_table)
    return SectionNodeAllocation(
        status=raw_node.status,
        node_total_cpu=raw_node.node_total_cpu,
        allocated_cpu=(
            sum(vm.maxcpu for vm in raw_node.running_vms)
            if raw_node.node_total_cpu is not None
            else None
        ),
        node_total_mem=raw_node.node_total_mem,
        allocated_mem=(
            sum(vm.maxmem for vm in raw_node.running_vms)
            if raw_node.node_total_mem is not None
            else None
        ),
    )


agent_section_proxmox_ve_node_allocation = AgentSection(
    name="proxmox_ve_node_allocation",
    parse_function=parse_proxmox_ve_node_allocation,
)

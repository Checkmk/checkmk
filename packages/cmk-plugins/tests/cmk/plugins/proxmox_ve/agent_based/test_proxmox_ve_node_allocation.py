#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from cmk.plugins.proxmox_ve.agent_based.proxmox_ve_node_allocation import (
    parse_proxmox_ve_node_allocation,
)
from cmk.plugins.proxmox_ve.lib.node_allocation import SectionNodeAllocation


def _string_table(raw: object) -> list[list[str]]:
    return [[json.dumps(raw)]]


def test_parse_proxmox_ve_node_allocation() -> None:
    raw = {
        "status": "online",
        "node_total_cpu": 32.0,
        "node_total_mem": 64000000.0,
        "running_vms": [
            {"vmid": "100", "maxcpu": 4.0, "maxmem": 8000000.0},
            {"vmid": "101", "maxcpu": 2.0, "maxmem": 4000000.0},
        ],
    }

    assert parse_proxmox_ve_node_allocation(_string_table(raw)) == SectionNodeAllocation(
        status="online",
        node_total_cpu=32.0,
        allocated_cpu=6.0,
        node_total_mem=64000000.0,
        allocated_mem=12000000.0,
    )


def test_parse_proxmox_ve_node_allocation_no_running_vms() -> None:
    raw = {
        "status": "online",
        "node_total_cpu": 32.0,
        "node_total_mem": 64000000.0,
        "running_vms": [],
    }

    assert parse_proxmox_ve_node_allocation(_string_table(raw)) == SectionNodeAllocation(
        status="online",
        node_total_cpu=32.0,
        allocated_cpu=0.0,
        node_total_mem=64000000.0,
        allocated_mem=0.0,
    )


def test_parse_proxmox_ve_node_allocation_missing_maxcpu_maxmem() -> None:
    raw = {
        "status": "online",
        "node_total_cpu": None,
        "node_total_mem": None,
        "running_vms": [
            {"vmid": "100", "maxcpu": 4.0, "maxmem": 8000000.0},
        ],
    }

    assert parse_proxmox_ve_node_allocation(_string_table(raw)) == SectionNodeAllocation(
        status="online",
        node_total_cpu=None,
        allocated_cpu=None,
        node_total_mem=None,
        allocated_mem=None,
    )

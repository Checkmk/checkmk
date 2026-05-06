#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.proxmox_ve.agent_based.proxmox_ve_node_cpu_allocation import (
    check_proxmox_ve_node_cpu_allocation,
    discover_proxmox_ve_node_cpu_allocation,
    Params,
)
from cmk.plugins.proxmox_ve.lib.node_allocation import SectionNodeAllocation

SECTION = SectionNodeAllocation(
    allocated_cpu=20.0,
    node_total_cpu=13.0,
    allocated_mem=32000000.0,
    node_total_mem=64000000.0,
    status="ok",
)

SECTION_NO_CPU = SectionNodeAllocation(
    allocated_cpu=None,
    node_total_cpu=None,
    allocated_mem=32000000.0,
    node_total_mem=64000000.0,
    status="ok",
)


def test_discover_proxmox_ve_node_cpu_allocation() -> None:
    assert list(discover_proxmox_ve_node_cpu_allocation(SECTION)) == [Service()]


def test_discover_proxmox_ve_node_cpu_allocation_missing_data() -> None:
    assert list(discover_proxmox_ve_node_cpu_allocation(SECTION_NO_CPU)) == []


@pytest.mark.parametrize(
    "params,section,expected_result",
    [
        pytest.param(
            {
                "cpu_allocation_ratio": ("fixed", (120, 150)),
            },
            SECTION,
            [
                Result(
                    state=State.CRIT,
                    summary="CPU allocation ratio: 153.85% (warn/crit at 120.00%/150.00%)",
                ),
                Metric("node_cpu_allocation_ratio", 153.84615384615387, levels=(120.0, 150.0)),
                Result(state=State.OK, summary="Allocated CPUs: 20"),
            ],
            id="CRIT, with Levels",
        ),
        pytest.param(
            {
                "cpu_allocation_ratio": ("no_levels", None),
            },
            SECTION,
            [
                Result(state=State.OK, summary="CPU allocation ratio: 153.85%"),
                Metric("node_cpu_allocation_ratio", 153.84615384615387),
                Result(state=State.OK, summary="Allocated CPUs: 20"),
            ],
            id="Everything OK, no Levels",
        ),
        pytest.param(
            {
                "cpu_allocation_ratio": ("no_levels", None),
            },
            SECTION_NO_CPU,
            [],
            id="No output when maxcpu not reported",
        ),
        pytest.param(
            {
                "cpu_allocation_ratio": ("no_levels", None),
            },
            SectionNodeAllocation(
                allocated_cpu=20.0,
                node_total_cpu=None,
                allocated_mem=32000000.0,
                node_total_mem=64000000.0,
                status="ok",
            ),
            [],
            id="No output when node total cpu is missing",
        ),
    ],
)
def test_check_proxmox_ve_node_cpu_allocation(
    params: Params,
    section: SectionNodeAllocation,
    expected_result: CheckResult,
) -> None:
    assert list(check_proxmox_ve_node_cpu_allocation(params, section)) == expected_result

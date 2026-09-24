#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.proxmox_ve.agent_based.proxmox_ve_node_mem_allocation import (
    check_proxmox_ve_node_mem_allocation,
    discover_proxmox_ve_node_mem_allocation,
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

SECTION_NO_MEM = SectionNodeAllocation(
    allocated_cpu=20.0,
    node_total_cpu=13.0,
    allocated_mem=None,
    node_total_mem=None,
    status="ok",
)


def test_discover_proxmox_ve_node_mem_allocation() -> None:
    assert list(discover_proxmox_ve_node_mem_allocation(SECTION)) == [Service()]


def test_discover_proxmox_ve_node_mem_allocation_missing_data() -> None:
    assert list(discover_proxmox_ve_node_mem_allocation(SECTION_NO_MEM)) == []


@pytest.mark.parametrize(
    "params,section,expected_result",
    [
        pytest.param(
            {
                "mem_allocation_ratio": ("fixed", (30.0, 50.0)),
            },
            SECTION,
            [
                Result(
                    state=State.CRIT,
                    summary="Memory allocation ratio: 50.00% (warn/crit at 30.00%/50.00%)",
                ),
                Metric("node_mem_allocation_ratio", 50.0, levels=(30.0, 50.0)),
                Result(state=State.OK, summary="Allocated Memory: 30.5 MiB"),
            ],
            id="CRIT, with Levels",
        ),
        pytest.param(
            {
                "mem_allocation_ratio": ("no_levels", None),
            },
            SECTION,
            [
                Result(state=State.OK, summary="Memory allocation ratio: 50.00%"),
                Metric("node_mem_allocation_ratio", 50.0),
                Result(state=State.OK, summary="Allocated Memory: 30.5 MiB"),
            ],
            id="Everything OK, no Levels",
        ),
        pytest.param(
            {
                "mem_allocation_ratio": ("no_levels", None),
            },
            SECTION_NO_MEM,
            [],
            id="No output when maxmem not reported",
        ),
        pytest.param(
            {
                "mem_allocation_ratio": ("no_levels", None),
            },
            SectionNodeAllocation(
                allocated_cpu=20.0,
                node_total_cpu=13.0,
                allocated_mem=32000000.0,
                node_total_mem=None,
                status="ok",
            ),
            [],
            id="No output when node total mem is missing",
        ),
        pytest.param(
            {
                "mem_allocation_ratio": ("fixed", (100.0, 120.0)),
            },
            # An offline node is reported with all totals set to 0
            SectionNodeAllocation(
                allocated_cpu=0.0,
                node_total_cpu=0.0,
                allocated_mem=0.0,
                node_total_mem=0.0,
                status="offline",
            ),
            [
                Result(
                    state=State.OK,
                    summary=(
                        "Node status: offline, total memory: 0 B, "
                        "cannot calculate memory allocation ratio"
                    ),
                ),
            ],
            id="Offline node with node total mem 0",
            marks=pytest.mark.xfail(
                strict=True,
                reason="Crash report 31915e7f-484d-11f1-8000-005056a019b7: ZeroDivisionError",
            ),
        ),
        pytest.param(
            {
                "mem_allocation_ratio": ("fixed", (100.0, 120.0)),
            },
            # An offline node can still report the totals of its last known stats
            SectionNodeAllocation(
                allocated_cpu=0.0,
                node_total_cpu=13.0,
                allocated_mem=0.0,
                node_total_mem=64000000.0,
                status="offline",
            ),
            [
                Result(
                    state=State.OK,
                    summary=(
                        "Node status: offline, total memory: 61.0 MiB, "
                        "cannot calculate memory allocation ratio"
                    ),
                ),
            ],
            id="Offline node with node total mem reported",
            marks=pytest.mark.xfail(
                strict=True,
                reason="Crash report 31915e7f-484d-11f1-8000-005056a019b7: ZeroDivisionError",
            ),
        ),
        pytest.param(
            {
                "mem_allocation_ratio": ("fixed", (100.0, 120.0)),
            },
            SectionNodeAllocation(
                allocated_cpu=0.0,
                node_total_cpu=0.0,
                allocated_mem=0.0,
                node_total_mem=0.0,
                status="online",
            ),
            [
                Result(
                    state=State.OK,
                    summary=(
                        "Node status: online, total memory: 0 B, "
                        "cannot calculate memory allocation ratio"
                    ),
                ),
            ],
            id="Online node with node total mem 0",
            marks=pytest.mark.xfail(
                strict=True,
                reason="Crash report 31915e7f-484d-11f1-8000-005056a019b7: ZeroDivisionError",
            ),
        ),
    ],
)
def test_check_proxmox_ve_node_mem_allocation(
    params: Params,
    section: SectionNodeAllocation,
    expected_result: CheckResult,
) -> None:
    assert list(check_proxmox_ve_node_mem_allocation(params, section)) == expected_result

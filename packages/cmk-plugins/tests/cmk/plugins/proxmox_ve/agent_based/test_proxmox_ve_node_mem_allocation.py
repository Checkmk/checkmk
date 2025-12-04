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


def test_discover_proxmox_ve_node_mem_allocation() -> None:
    assert list(discover_proxmox_ve_node_mem_allocation(SECTION)) == [Service()]


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
    ],
)
def test_check_proxmox_ve_node_mem_allocation(
    params: Params,
    section: SectionNodeAllocation,
    expected_result: CheckResult,
) -> None:
    assert list(check_proxmox_ve_node_mem_allocation(params, section)) == expected_result

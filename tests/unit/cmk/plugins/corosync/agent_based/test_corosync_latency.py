#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.corosync.agent_based.corosync_latency import (
    check_corosync_latency,
    discover_corosync_latency,
    Link,
    Params,
    parse_corosync_latency,
    SectionCorosyncLatency,
)

STRING_TABLE = string_table = [
    ["stats.knet.node1.link0.connected", "(u8)", "=", "1"],
    ["stats.knet.node1.link0.latency_ave", "(u32)", "=", "0"],
    ["stats.knet.node1.link0.latency_max", "(u32)", "=", "0"],
    ["stats.knet.node1.link0.latency_min", "(u32)", "=", "0"],
    ["stats.knet.node1.link0.latency_samples", "(u32)", "=", "0"],
    ["stats.knet.node1.link1.connected", "(u8)", "=", "1"],
    ["stats.knet.node1.link1.latency_ave", "(u32)", "=", "15000"],
    ["stats.knet.node1.link1.latency_max", "(u32)", "=", "25000"],
    ["stats.knet.node1.link1.latency_min", "(u32)", "=", "10"],
    ["stats.knet.node1.link1.latency_samples", "(u32)", "=", "100"],
    ["stats.knet.node2.link0.connected", "(u8)", "=", "0"],
    ["stats.knet.node2.link0.latency_ave", "(u32)", "=", "0"],
    ["stats.knet.node2.link0.latency_max", "(u32)", "=", "0"],
    ["stats.knet.node2.link0.latency_min", "(u32)", "=", "0"],
    ["stats.knet.node2.link0.latency_samples", "(u32)", "=", "0"],
]

SECTION = {
    "node1.link0": Link(
        hostname="node1",
        name="link0",
        connected=True,
        latency_ave=0.0,
        latency_max=0.0,
        latency_min=0.0,
        latency_samples=0.0,
    ),
    "node1.link1": Link(
        hostname="node1",
        name="link1",
        connected=True,
        latency_ave=15000.0,
        latency_max=25000.0,
        latency_min=10.0,
        latency_samples=100.0,
    ),
    "node2.link0": Link(
        hostname="node2",
        name="link0",
        connected=False,
        latency_ave=0.0,
        latency_max=0.0,
        latency_min=0.0,
        latency_samples=0.0,
    ),
}


def test_parse_corosync_latency() -> None:
    assert parse_corosync_latency(STRING_TABLE) == SECTION
    assert parse_corosync_latency([[]]) == {}


def test_discover_corosync_latency() -> None:
    assert list(discover_corosync_latency(SECTION)) == [
        Service(item="node1.link1"),
        Service(item="node2.link0"),
    ]


@pytest.mark.parametrize(
    "item, section, params, expected_result",
    [
        pytest.param(
            "node1.link1",
            SECTION,
            {"latency_max": ("fixed", (0.02, 0.03)), "latency_ave": ("fixed", (0.01, 0.02))},
            [
                Result(
                    state=State.WARN,
                    summary="Latency Max: 25 milliseconds (warn/crit at 20 milliseconds/30 milliseconds)",
                ),
                Metric("latency_max", 0.025, levels=(0.02, 0.03)),
                Result(
                    state=State.WARN,
                    summary="Latency Average: 15 milliseconds (warn/crit at 10 milliseconds/20 milliseconds)",
                ),
                Metric("latency_ave", 0.015, levels=(0.01, 0.02)),
            ],
            id="node1.link1 -> WARN/WARN because of levels",
        ),
        pytest.param(
            "node2.link0",
            SECTION,
            {"latency_max": ("no_levels", None), "latency_ave": ("no_levels", None)},
            [Result(state=State.CRIT, summary="Link is not connected or down")],
            id="node2.link0 -> CRIT because link is down (no results)",
        ),
        pytest.param(
            "random.link",
            SECTION,
            {"latency_max": ("no_levels", None), "latency_ave": ("no_levels", None)},
            [],
            id="No results because item not in section",
        ),
    ],
)
def test_check_corosync_latency(
    item: str, section: SectionCorosyncLatency, params: Params, expected_result: CheckResult
) -> None:
    assert list(check_corosync_latency(item, params, section)) == expected_result

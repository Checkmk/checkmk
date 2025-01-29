#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.collection.agent_based import tsm_stagingpools

SECTION = {"bar": ["99.9", "97.9"], "foo": ["7.1"]}
NODE_SECTION = {"node1": SECTION, "node2": SECTION, "node3": {"foo": ["7.1", "9.3"]}}


@pytest.mark.parametrize(
    "item, params, expected",
    [
        ("not-existant", tsm_stagingpools.TSM_STAGINGPOOLS_DEFAULT_LEVELS, []),
        (
            "foo",
            tsm_stagingpools.TSM_STAGINGPOOLS_DEFAULT_LEVELS,
            [
                Result(
                    state=State.OK,
                    summary="Total tapes: 1, Utilization: 0.1 tapes, Tapes less then 70% full: 1",
                    details="Total tapes: 1, Utilization: 0.1 tapes, Tapes less then 70% full: 1",
                ),
                Metric("free", 1.0, boundaries=(0.0, 1.0)),
                Metric("tapes", 1.0),
                Metric("util", 0.071),
            ],
        ),
        (
            "bar",
            {"levels": (2, 1), "free_below": 70},
            [
                Result(
                    state=State.CRIT,
                    summary="Total tapes: 2, Utilization: 2.0 tapes, Tapes less then 70% full: 0 (warn/crit below 2/1)",
                    details="Total tapes: 2, Utilization: 2.0 tapes, Tapes less then 70% full: 0 (warn/crit below 2/1)",
                ),
                Metric("free", 0.0, boundaries=(0.0, 2.0)),
                Metric("tapes", 2.0),
                Metric("util", 1.9780000000000002),
            ],
        ),
    ],
)
def test_check(item: str, params: Mapping[str, object], expected: CheckResult) -> None:
    actual = list(tsm_stagingpools.check_tsm_stagingpools(item, params, SECTION))
    assert actual == expected


@pytest.mark.parametrize(
    "item, params, expected",
    [
        ("not-existant", tsm_stagingpools.TSM_STAGINGPOOLS_DEFAULT_LEVELS, []),
        (
            "foo",
            tsm_stagingpools.TSM_STAGINGPOOLS_DEFAULT_LEVELS,
            [
                Result(state=State.OK, summary="node1/node2/node3: "),
                Result(
                    state=State.OK,
                    summary="Total tapes: 1, Utilization: 0.1 tapes, Tapes less then 70% full: 1",
                    details="Total tapes: 1, Utilization: 0.1 tapes, Tapes less then 70% full: 1",
                ),
                Metric("free", 1.0, boundaries=(0.0, 1.0)),
                Metric("tapes", 1.0),
                Metric("util", 0.071),
                Result(
                    state=State.UNKNOWN,
                    summary="Cluster: data from nodes are not equal",
                    details="Cluster: data from nodes are not equal",
                ),
            ],
        ),
        (
            "bar",
            {"levels": (2, 1), "free_below": 70},
            [
                Result(state=State.OK, summary="node1/node2: "),
                Result(
                    state=State.CRIT,
                    summary="Total tapes: 2, Utilization: 2.0 tapes, Tapes less then 70% full: 0 (warn/crit below 2/1)",
                    details="Total tapes: 2, Utilization: 2.0 tapes, Tapes less then 70% full: 0 (warn/crit below 2/1)",
                ),
                Metric("free", 0.0, boundaries=(0.0, 2.0)),
                Metric("tapes", 2.0),
                Metric("util", 1.9780000000000002),
            ],
        ),
    ],
)
def test_cluster_check(item: str, params: Mapping[str, object], expected: CheckResult) -> None:
    actual = list(tsm_stagingpools.cluster_check_tsm_stagingspools(item, params, NODE_SECTION))
    assert actual == expected

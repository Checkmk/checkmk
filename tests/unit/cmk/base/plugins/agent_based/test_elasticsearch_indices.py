#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.elasticsearch_indices import (
    _check_elasticsearch_indices,
    _CheckParams,
    _Section,
    discover_elasticsearch_indices,
    parse_elasticsearch_indices,
)


@pytest.fixture(name="section", scope="module")
def _section() -> _Section:
    return parse_elasticsearch_indices(
        [
            [".monitoring-kibana-6", "971.0", "765236.0"],
            ["filebeat", "28398.0", "22524354.0"],
            [".monitoring-es-6", "11986.0", "15581765.0"],
        ]
    )


def test_discover(section: _Section) -> None:
    assert list(discover_elasticsearch_indices(section)) == [
        Service(item=".monitoring-kibana-6"),
        Service(item="filebeat"),
        Service(item=".monitoring-es-6"),
    ]


@pytest.mark.parametrize(
    ["item", "params", "expected_result"],
    [
        pytest.param(
            "filebeat",
            {},
            [
                Result(state=State.OK, summary="Document count: 28398"),
                Metric("elasticsearch_count", 28398.0),
                Result(state=State.OK, summary="Document count rate: 30/minute"),
                Metric("elasticsearch_count_rate", 30.0),
                Result(state=State.OK, summary="Size: 21.5 MiB"),
                Metric("elasticsearch_size", 22524354.0),
                Result(state=State.OK, summary="Size rate: 293 KiB/minute"),
                Metric("elasticsearch_size_rate", 300000.0),
            ],
            id="without params",
        ),
        pytest.param(
            "filebeat",
            {
                "elasticsearch_count_rate": (10, 20, 2),
                "elasticsearch_size_rate": (5, 15, 2),
            },
            [
                Result(state=State.OK, summary="Document count: 28398"),
                Metric("elasticsearch_count", 28398.0),
                Result(
                    state=State.CRIT,
                    summary="Document count rate: 30/minute (warn/crit at 25/minute/27/minute)",
                ),
                Metric(
                    "elasticsearch_count_rate",
                    30.0,
                    levels=(24.639341968612495, 26.879282147577268),
                ),
                Result(state=State.OK, summary="Size: 21.5 MiB"),
                Metric("elasticsearch_size", 22524354.0),
                Result(
                    state=State.CRIT,
                    summary="Size rate: 293 KiB/minute (warn/crit at 230 KiB/minute/252 KiB/minute)",
                ),
                Metric(
                    "elasticsearch_size_rate",
                    300000.0,
                    levels=(235193.71879130113, 257593.12058094883),
                ),
            ],
            id="with params",
        ),
        pytest.param(
            "missing",
            {},
            [],
            id="missing item",
        ),
    ],
)
def test_check(
    section: _Section,
    item: str,
    params: _CheckParams,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            _check_elasticsearch_indices(
                item=item,
                params=params,
                section=section,
                value_store={
                    "elasticsearch_count": (100.0, 28298.0),
                    "elasticsearch_count.average": (100.0, 100.0, 0.0),
                    "elasticsearch_size": (100.0, 21524354.0),
                    "elasticsearch_size.average": (100.0, 100.0, 0.0),
                },
                now=300,
            )
        )
        == expected_result
    )

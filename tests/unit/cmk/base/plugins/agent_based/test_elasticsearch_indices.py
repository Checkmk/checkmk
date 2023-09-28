#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from cmk.base.plugins.agent_based.elasticsearch_indices import (
    _check_elasticsearch_indices,
    _CheckParams,
    _DiscoveryParams,
    _Section,
    discover_elasticsearch_indices,
    parse_elasticsearch_indices,
)


@pytest.fixture(name="section", scope="module")
def _section() -> _Section:
    return parse_elasticsearch_indices(
        [
            [
                json.dumps(
                    {
                        "my-index-10.2022": {
                            "uuid": "eZx4bV5_Qta1ErK6wftxHw",
                            "health": "yellow",
                            "status": "open",
                            "primaries": {
                                "docs": {"count": 28398, "deleted": 0},
                                "store": {
                                    "size_in_bytes": 22524354,
                                    "total_data_set_size_in_bytes": 22524354,
                                    "reserved_in_bytes": 0,
                                },
                            },
                            "total": {
                                "docs": {"count": 28398, "deleted": 0},
                                "store": {
                                    "size_in_bytes": 22524354,
                                    "total_data_set_size_in_bytes": 22524354,
                                    "reserved_in_bytes": 0,
                                },
                            },
                        },
                        "my-index-11.2022": {
                            "uuid": "gP4TQ0PcSS6p3E0ULgqH5g",
                            "health": "yellow",
                            "status": "open",
                            "primaries": {
                                "docs": {"count": 2, "deleted": 4},
                                "store": {
                                    "size_in_bytes": 35800,
                                    "total_data_set_size_in_bytes": 35800,
                                    "reserved_in_bytes": 0,
                                },
                            },
                            "total": {
                                "docs": {"count": 2, "deleted": 4},
                                "store": {
                                    "size_in_bytes": 35800,
                                    "total_data_set_size_in_bytes": 35800,
                                    "reserved_in_bytes": 0,
                                },
                            },
                        },
                        "my-other-index-2016-04-12": {
                            "uuid": "MOEas2q8QyWHKsNFh3_7NA",
                            "health": "yellow",
                            "status": "open",
                            "primaries": {
                                "docs": {"count": 28248, "deleted": 0},
                                "store": {
                                    "size_in_bytes": 35801234,
                                    "total_data_set_size_in_bytes": 35801234,
                                    "reserved_in_bytes": 0,
                                },
                            },
                            "total": {
                                "docs": {"count": 28248, "deleted": 0},
                                "store": {
                                    "size_in_bytes": 35801234,
                                    "total_data_set_size_in_bytes": 35801234,
                                    "reserved_in_bytes": 0,
                                },
                            },
                        },
                        "my-other-index-2016-04-22": {
                            "uuid": "VsVq79a4T423GoBwS7hFFw",
                            "health": "yellow",
                            "status": "open",
                            "primaries": {
                                "docs": {"count": 128248, "deleted": 0},
                                "store": {
                                    "size_in_bytes": 69174895,
                                    "total_data_set_size_in_bytes": 69174895,
                                    "reserved_in_bytes": 0,
                                },
                            },
                            "total": {
                                "docs": {"count": 128248, "deleted": 0},
                                "store": {
                                    "size_in_bytes": 69174895,
                                    "total_data_set_size_in_bytes": 69174895,
                                    "reserved_in_bytes": 0,
                                },
                            },
                        },
                        "yet_another_index": {
                            "uuid": "cft6yprDQaW9P5ILuFQ0ow",
                            "health": "yellow",
                            "status": "open",
                            "primaries": {
                                "docs": {"count": 22, "deleted": 0},
                                "store": {
                                    "size_in_bytes": 21680,
                                    "total_data_set_size_in_bytes": 21680,
                                    "reserved_in_bytes": 0,
                                },
                            },
                            "total": {
                                "docs": {"count": 22, "deleted": 0},
                                "store": {
                                    "size_in_bytes": 21680,
                                    "total_data_set_size_in_bytes": 21680,
                                    "reserved_in_bytes": 0,
                                },
                            },
                        },
                    }
                )
            ]
        ]
    )


@pytest.mark.parametrize(
    ["params", "expected_result"],
    [
        pytest.param(
            {"grouping": ("disabled", [])},
            [
                Service(item="my-index-10.2022", parameters={"grouping_regex": None}),
                Service(item="my-index-11.2022", parameters={"grouping_regex": None}),
                Service(item="my-other-index-2016-04-12", parameters={"grouping_regex": None}),
                Service(item="my-other-index-2016-04-22", parameters={"grouping_regex": None}),
                Service(item="yet_another_index", parameters={"grouping_regex": None}),
            ],
            id="no grouping",
        ),
        pytest.param(
            {"grouping": ("enabled", ["my-index", "my-other-index"])},
            [
                Service(item="my-index", parameters={"grouping_regex": "my-index"}),
                Service(item="my-other-index", parameters={"grouping_regex": "my-other-index"}),
                Service(item="yet_another_index", parameters={"grouping_regex": None}),
            ],
            id="manual grouping",
        ),
        pytest.param(
            {"grouping": ("enabled", ["my-([a-z]|-)+[a-z]"])},
            [
                Service(item="my-index", parameters={"grouping_regex": "my-([a-z]|-)+[a-z]"}),
                Service(
                    item="my-other-index",
                    parameters={"grouping_regex": "my-([a-z]|-)+[a-z]"},
                ),
                Service(item="yet_another_index", parameters={"grouping_regex": None}),
            ],
            id="more advanced grouping",
        ),
        pytest.param(
            {"grouping": ("enabled", ["my-index", "[0-9]*my-index"])},
            [
                Service(item="my-index", parameters={"grouping_regex": "my-index"}),
                Service(item="my-other-index-2016-04-12", parameters={"grouping_regex": None}),
                Service(item="my-other-index-2016-04-22", parameters={"grouping_regex": None}),
                Service(item="yet_another_index", parameters={"grouping_regex": None}),
            ],
            id="overlapping groups",
        ),
    ],
)
def test_discover(
    section: _Section,
    params: _DiscoveryParams,
    expected_result: DiscoveryResult,
) -> None:
    assert sorted(discover_elasticsearch_indices(params, section)) == expected_result


@pytest.mark.parametrize(
    ["item", "params", "expected_result"],
    [
        pytest.param(
            "my-index-10.2022",
            {"grouping_regex": None},
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
            id="ungrouped, without thresholds",
        ),
        pytest.param(
            "my-index",
            {"grouping_regex": "my-index"},
            [
                Result(state=State.OK, summary="Document count: 14200"),
                Metric("elasticsearch_count", 14200.0),
                Result(state=State.OK, summary="Document count rate: -4229/minute"),
                Metric("elasticsearch_count_rate", -4229.4),
                Result(state=State.OK, summary="Size: 10.8 MiB"),
                Metric("elasticsearch_size", 11280077.0),
                Result(state=State.OK, summary="Size rate: -2.93 MiB/minute"),
                Metric("elasticsearch_size_rate", -3073283.1),
            ],
            id="grouped, without thresholds",
        ),
        pytest.param(
            "my-other-index-2016-04-12",
            {
                "grouping_regex": None,
                "elasticsearch_count_rate": (10, 20, 2),
                "elasticsearch_size_rate": (5, 15, 2),
            },
            [
                Result(state=State.OK, summary="Document count: 28248"),
                Metric("elasticsearch_count", 28248.0),
                Result(state=State.OK, summary="Document count rate: -15/minute"),
                Metric(
                    "elasticsearch_count_rate",
                    -15.0,
                    levels=(-12.319670984306248, -13.439641073788634),
                ),
                Result(state=State.OK, summary="Size: 34.1 MiB"),
                Metric("elasticsearch_size", 35801234.0),
                Result(
                    state=State.CRIT,
                    summary="Size rate: 4.08 MiB/minute (warn/crit at 3.20 MiB/minute/3.51 MiB/minute)",
                ),
                Metric(
                    "elasticsearch_size_rate",
                    4283064.0,
                    levels=(3357832.499937151, 3677626.0713597364),
                ),
            ],
            id="ungrouped, with thresholds",
        ),
        pytest.param(
            "my-other-index",
            {
                "grouping_regex": "my-other-index",
                "elasticsearch_count_rate": (10, 20, 2),
                "elasticsearch_size_rate": (5, 15, 2),
            },
            [
                Result(state=State.OK, summary="Document count: 78248"),
                Metric("elasticsearch_count", 78248.0),
                Result(
                    state=State.CRIT,
                    summary="Document count rate: 14985/minute (warn/crit at 12307/minute/13426/minute)",
                ),
                Metric(
                    "elasticsearch_count_rate",
                    14985.0,
                    levels=(12307.351313321942, 13426.201432714844),
                ),
                Result(state=State.OK, summary="Size: 50.1 MiB"),
                Metric("elasticsearch_size", 52488064.5),
                Result(
                    state=State.CRIT,
                    summary="Size rate: 8.86 MiB/minute (warn/crit at 6.95 MiB/minute/7.61 MiB/minute)",
                ),
                Metric(
                    "elasticsearch_size_rate",
                    9289113.149999999,
                    levels=(7282470.220072256, 7976038.812460089),
                ),
            ],
            id="grouped, with thresholds",
        ),
        pytest.param(
            "my-index-10.2022",
            {"grouping_regex": "my-index-10.2022"},
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
            id="group with one member",
        ),
        pytest.param(
            "missing",
            {"grouping_regex": None},
            [],
            id="ungrouped, missing item",
        ),
        pytest.param(
            "missing",
            {"grouping_regex": "missing"},
            [],
            id="group empty",
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

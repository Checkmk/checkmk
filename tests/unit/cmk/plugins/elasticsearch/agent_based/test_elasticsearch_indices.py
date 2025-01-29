#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Final

import pytest

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Metric, Result, Service, State
from cmk.plugins.elasticsearch.agent_based.elasticsearch_indices import (
    _check_elasticsearch_indices,
    _CheckParams,
    _DiscoveryParams,
    discover_elasticsearch_indices,
    parse_elasticsearch_indices,
)

SECTION: Final = parse_elasticsearch_indices(
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
    params: _DiscoveryParams,
    expected_result: DiscoveryResult,
) -> None:
    assert sorted(discover_elasticsearch_indices(params, SECTION)) == expected_result


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
                Result(state=State.OK, summary="Document count: 28400"),
                Metric("elasticsearch_count", 28400.0),
                Result(state=State.OK, summary="Document count rate: 31/minute"),
                Metric("elasticsearch_count_rate", 30.6),
                Result(state=State.OK, summary="Size: 21.5 MiB"),
                Metric("elasticsearch_size", 22560154.0),
                Result(state=State.OK, summary="Size rate: 303 KiB/minute"),
                Metric("elasticsearch_size_rate", 310740.0),
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
                    levels=(-11.302825669183648, -12.33035527547307),
                ),
                Result(state=State.OK, summary="Size: 34.1 MiB"),
                Metric("elasticsearch_size", 35801234.0),
                Result(
                    state=State.CRIT,
                    summary="Size rate: 4.08 MiB/minute (warn/crit at 2.94 MiB/minute/3.22 MiB/minute)",
                ),
                Metric(
                    "elasticsearch_size_rate",
                    4283064.0,
                    levels=(3080682.5459426795, 3374080.8836515057),
                ),
            ],
            id="ungrouped, with thresholds",
        ),
        pytest.param(
            "my-other-index",
            {
                "grouping_regex": "my-other-index",
                "elasticsearch_count_rate": (20, 30, 2),
                "elasticsearch_size_rate": (5, 15, 2),
            },
            [
                Result(state=State.OK, summary="Document count: 156496"),
                Metric("elasticsearch_count", 156496.0),
                Result(
                    state=State.CRIT,
                    summary="Document count rate: 38459/minute (warn/crit at 31615/minute/34249/minute)",
                ),
                Metric(
                    "elasticsearch_count_rate",
                    38459.4,
                    levels=(31614.53771210193, 34249.08252144376),
                ),
                Result(state=State.OK, summary="Size: 100 MiB"),
                Metric("elasticsearch_size", 104976129.0),
                Result(
                    state=State.CRIT,
                    summary="Size rate: 23.9 MiB/minute (warn/crit at 17.2 MiB/minute/18.8 MiB/minute)",
                ),
                Metric(
                    "elasticsearch_size_rate",
                    25035532.5,
                    levels=(18007325.59707973, 19722308.9872778),
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
    item: str,
    params: _CheckParams,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            _check_elasticsearch_indices(
                item=item,
                params=params,
                section=SECTION,
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

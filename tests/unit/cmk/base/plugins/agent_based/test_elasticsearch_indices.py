#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

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
                                "docs": {"count": 1, "deleted": 0},
                                "store": {
                                    "size_in_bytes": 3580,
                                    "total_data_set_size_in_bytes": 3580,
                                    "reserved_in_bytes": 0,
                                },
                            },
                            "total": {
                                "docs": {"count": 1, "deleted": 0},
                                "store": {
                                    "size_in_bytes": 3580,
                                    "total_data_set_size_in_bytes": 3580,
                                    "reserved_in_bytes": 0,
                                },
                            },
                        },
                        "my-other-index-2016-04-22": {
                            "uuid": "VsVq79a4T423GoBwS7hFFw",
                            "health": "yellow",
                            "status": "open",
                            "primaries": {
                                "docs": {"count": 2, "deleted": 0},
                                "store": {
                                    "size_in_bytes": 6917,
                                    "total_data_set_size_in_bytes": 6917,
                                    "reserved_in_bytes": 0,
                                },
                            },
                            "total": {
                                "docs": {"count": 2, "deleted": 0},
                                "store": {
                                    "size_in_bytes": 6917,
                                    "total_data_set_size_in_bytes": 6917,
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


def test_discover(section: _Section) -> None:
    assert sorted(discover_elasticsearch_indices(section)) == [
        Service(item="my-index-10.2022"),
        Service(item="my-index-11.2022"),
        Service(item="my-other-index-2016-04-12"),
        Service(item="my-other-index-2016-04-22"),
        Service(item="yet_another_index"),
    ]


@pytest.mark.parametrize(
    ["item", "params", "expected_result"],
    [
        pytest.param(
            "my-index-10.2022",
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
            "my-index-10.2022",
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

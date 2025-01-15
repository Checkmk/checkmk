#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.gcp.agent_based.gcp_cost import check, discover, parse, Section

TABLE_MULTI_MONTH = [
    ['{"query_month": "202501"}'],
    ['{"project": "th", "id": "th", "month": "202501", "amount": 4.2, "currency": "EUR"}'],
    ['{"project": "th", "id": "th", "month": "202411", "amount": 0.039882, "currency": "EUR"}'],
    ['{"project": "th", "id": "th", "month": "202412", "amount": 7.0, "currency": "EUR"}'],
    ['{"project": "La", "id": "la", "month": "202501", "amount": 0.00, "currency": "EUR"}'],
]


@pytest.fixture(name="section")
def _section() -> Section:
    table = [
        ['{"query_month":  "202207" }'],
        [
            '{"project": "test", "id": "test1", "month": "202207", "amount": 42.21, "currency": "EUR"}'
        ],
        [
            '{"project": "checkmk", "id": "checkmk", "month": "202207", "amount": 3.1415, "currency": "EUR"}'
        ],
        [
            '{"project": "test", "id": "test1", "month": "202206", "amount": 1337.0, "currency": "EUR"}'
        ],
        [
            '{"project": "test", "id": "test2", "month": "202207", "amount": 42.21, "currency": "EUR"}'
        ],
        [
            '{"project": "test", "id": "test2", "month": "202206", "amount": 1337.0, "currency": "EUR"}'
        ],
        [
            '{"project": "checkmk", "id": "checkmk", "month": "202206", "amount": 2.71, "currency": "EUR"}'
        ],
        [
            '{"project": "single", "id": "single", "month": "202207", "amount": 2.71, "currency": "EUR"}'
        ],
        # if we do not have data for the query month exclude project
        [
            '{"project": "exclude", "id": "exclude", "month": "202206", "amount": 2.71, "currency": "EUR"}'
        ],
    ]
    return parse(table)


def test_gcp_multi_month(section: Section) -> None:
    assert list(sorted(discover(parse(TABLE_MULTI_MONTH)))) == [
        Service(item="la"),
        Service(item="th"),
    ]


def test_gcp_cost_discovery(section: Section) -> None:
    services = list(discover(section))
    assert sorted(services) == sorted(
        [
            Service(item="checkmk"),
            Service(item="single"),
            Service(item="test1"),
            Service(item="test2"),
        ]
    )


@pytest.mark.parametrize("item", ["test1", "test2"])
def test_gcp_cost_check(section: Section, item: str) -> None:
    results = list(check(item=item, params={"levels": None}, section=section))
    assert results == [
        Result(state=State.OK, summary="July 2022: 42.21 EUR"),
        Metric("gcp_cost_per_month", 42.21),
    ]


def test_gcp_cost_check_data_only_one_month(section: Section) -> None:
    results = list(check(item="single", params={"levels": None}, section=section))
    assert results == [
        Result(state=State.OK, summary="July 2022: 2.71 EUR"),
        Metric("gcp_cost_per_month", 2.71),
    ]


def test_item_not_in_section_yields_no_result(section: Section) -> None:
    results = list(check(item="notthere", params={"levels": None}, section=section))
    assert len(results) == 0


@pytest.mark.parametrize(
    "result, params",
    [
        pytest.param(
            [
                Result(
                    state=State.WARN,
                    summary="July 2022: 42.21 EUR (warn/crit at 21.00 EUR/50.00 EUR)",
                ),
                Metric("gcp_cost_per_month", 42.21, levels=(21.0, 50.0)),
            ],
            {"levels": ("fixed", (21, 50))},
            id="warn",
        ),
        pytest.param(
            [
                Result(
                    state=State.CRIT,
                    summary="July 2022: 42.21 EUR (warn/crit at 21.00 EUR/41.00 EUR)",
                ),
                Metric("gcp_cost_per_month", 42.21, levels=(21.0, 41.0)),
            ],
            {"levels": ("fixed", (21, 41))},
            id="crit",
        ),
    ],
)
def test_gcp_cost_check_levels(
    result: list[Result | Metric], params: Mapping[str, Any], section: Section
) -> None:
    results = list(check(item="test1", params=params, section=section))
    assert results == result

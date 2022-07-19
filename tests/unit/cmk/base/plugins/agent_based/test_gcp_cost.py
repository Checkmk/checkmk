#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
from typing import Any, Mapping

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.gcp_cost import check, discover, parse, Section


@pytest.fixture(name="section")
def _section() -> Section:
    table = [
        ['{"query_month":  "202207" }'],
        ['{"project": "test", "month": "202207", "amount": 42.21, "currency": "EUR"}'],
        ['{"project": "checkmk", "month": "202207", "amount": 3.1415, "currency": "EUR"}'],
        ['{"project": "test", "month": "202206", "amount": 1337.0, "currency": "EUR"}'],
        ['{"project": "checkmk", "month": "202206", "amount": 2.71, "currency": "EUR"}'],
        ['{"project": "single", "month": "202207", "amount": 2.71, "currency": "EUR"}'],
        # if we do not have data for the query month exclude project
        ['{"project": "exclude", "month": "202206", "amount": 2.71, "currency": "EUR"}'],
    ]
    return parse(table)


def test_gcp_cost_discovery(section: Section) -> None:
    services = list(discover(section))
    assert sorted(services) == sorted(
        [Service(item="checkmk"), Service(item="single"), Service(item="test")]
    )


def test_gcp_cost_check(section: Section) -> None:
    results = list(check(item="test", params={"levels": None}, section=section))
    assert results == [
        Result(
            state=State.OK,
            summary="Cost: 42.21 EUR",
            details="July 2022: 42.21 EUR, June 2022: 1337.00 EUR",
        )
    ]


def test_gcp_cost_check_data_only_one_month(section: Section) -> None:
    results = list(check(item="single", params={"levels": None}, section=section))
    assert results == [
        Result(
            state=State.OK,
            summary="Cost: 2.71 EUR",
            details="July 2022: 2.71 EUR",
        )
    ]


@pytest.mark.parametrize(
    "state, params",
    [
        pytest.param(State.WARN, {"levels": (21, 50)}, id="warn"),
        pytest.param(State.CRIT, {"levels": (21, 41)}, id="crit"),
    ],
)
def test_gcp_cost_check_levels(section: Section, state: State, params: Mapping[str, Any]) -> None:
    results = list(check(item="test", params=params, section=section))
    assert results == [
        Result(
            state=state,
            summary="Cost: 42.21 EUR",
            details="July 2022: 42.21 EUR, June 2022: 1337.00 EUR",
        )
    ]

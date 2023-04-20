#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.primekey_hsm_battery_voltage import (
    check,
    discover,
    HSMBattery,
    parse,
)

_Section = {
    "1": HSMBattery(voltage=3.115, state_fail=False),
    "2": HSMBattery(voltage=5.5, state_fail=True),
}


def test_parse() -> None:
    assert parse([["3.115 V", "0", "5.5 V", "1"]]) == _Section


def test_discover() -> None:
    assert list(discover(section=_Section)) == [Service(item="1"), Service(item="2")]


@pytest.mark.parametrize(
    "input_item,input_params, expected_results",
    [
        (
            "1",
            {},
            [
                Result(state=State.OK, summary="PrimeKey HSM battery 1 status OK"),
                Result(state=State.OK, summary="3.115 V"),
                Metric("voltage", 3.115),
            ],
        ),
        (
            "2",
            {},
            [
                Result(state=State.CRIT, summary="PrimeKey HSM battery 2 status not OK"),
                Result(state=State.OK, summary="5.5 V"),
                Metric("voltage", 5.5),
            ],
        ),
        (
            "1",
            {"levels": (4.0, 5.0)},
            [
                Result(state=State.OK, summary="PrimeKey HSM battery 1 status OK"),
                Result(state=State.OK, summary="3.115 V"),
                Metric("voltage", 3.115, levels=(4.0, 5.0)),
            ],
        ),
        (
            "2",
            {"levels": (4.0, 5.0)},
            [
                Result(state=State.CRIT, summary="PrimeKey HSM battery 2 status not OK"),
                Result(state=State.CRIT, summary="5.5 V (warn/crit at 4.0 V/5.0 V)"),
                Metric("voltage", 5.5, levels=(4.0, 5.0)),
            ],
        ),
    ],
)
def test_check(
    input_item: str, input_params: Mapping[str, tuple[float, float]], expected_results: CheckResult
) -> None:
    assert list(check(item=input_item, params=input_params, section=_Section)) == expected_results

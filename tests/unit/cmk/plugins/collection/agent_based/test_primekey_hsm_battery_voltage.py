#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.collection.agent_based.primekey_hsm_battery_voltage import (
    check,
    discover,
    HSMBattery,
    parse,
)

_Section = {
    "1": HSMBattery(voltage=3.115, state_fail=False),
    "2": HSMBattery(voltage=5.5, state_fail=True),
}
_SectionWithoutVoltage = {
    "1": HSMBattery(voltage=None, state_fail=False),
    "2": HSMBattery(voltage=None, state_fail=True),
}
_SectionWithAbsence = {
    "1": HSMBattery(voltage="absence", state_fail=False),
    "2": HSMBattery(voltage=5.5, state_fail=False),
}


def test_parse() -> None:
    assert parse([["3.115 V", "0", "5.5 V", "1"]]) == _Section
    assert parse([["something", "0", "something_else", "1"]]) == _SectionWithoutVoltage
    assert parse([["External Battery: absence", "0", "5.5 V", "0"]]) == _SectionWithAbsence


def test_discover() -> None:
    assert list(discover(section=_Section)) == [Service(item="1"), Service(item="2")]


@pytest.mark.parametrize(
    "section, input_item, input_params, expected_results",
    [
        (
            _Section,
            "1",
            {},
            [
                Result(state=State.OK, summary="PrimeKey HSM battery 1 status OK"),
                Result(state=State.OK, summary="3.115 V"),
                Metric("voltage", 3.115),
            ],
        ),
        (
            _Section,
            "2",
            {},
            [
                Result(state=State.CRIT, summary="PrimeKey HSM battery 2 status not OK"),
                Result(state=State.OK, summary="5.5 V"),
                Metric("voltage", 5.5),
            ],
        ),
        (
            _Section,
            "1",
            {"levels": (4.0, 5.0)},
            [
                Result(state=State.OK, summary="PrimeKey HSM battery 1 status OK"),
                Result(state=State.OK, summary="3.115 V"),
                Metric("voltage", 3.115, levels=(4.0, 5.0)),
            ],
        ),
        (
            _Section,
            "2",
            {"levels": (4.0, 5.0)},
            [
                Result(state=State.CRIT, summary="PrimeKey HSM battery 2 status not OK"),
                Result(state=State.CRIT, summary="5.5 V (warn/crit at 4.0 V/5.0 V)"),
                Metric("voltage", 5.5, levels=(4.0, 5.0)),
            ],
        ),
        (
            _SectionWithoutVoltage,
            "1",
            {"levels": (4.0, 5.0)},
            [
                Result(state=State.OK, summary="PrimeKey HSM battery 1 status OK"),
            ],
        ),
        (
            _SectionWithoutVoltage,
            "2",
            {"levels": (4.0, 5.0)},
            [
                Result(state=State.CRIT, summary="PrimeKey HSM battery 2 status not OK"),
            ],
        ),
        (
            _SectionWithAbsence,
            "1",
            {"levels": (4.0, 5.0)},
            [
                Result(state=State.OK, summary="PrimeKey HSM battery 1 status absence"),
            ],
        ),
    ],
)
def test_check(
    section: Mapping[str, HSMBattery],
    input_item: str,
    input_params: Mapping[str, tuple[float, float]],
    expected_results: CheckResult,
) -> None:
    assert list(check(item=input_item, params=input_params, section=section)) == expected_results

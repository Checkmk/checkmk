#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.primekey_fan import _Section, check, discover, Fan, parse

_SectionOk = {
    "CPU": Fan(speed=1000.0, state_fail=False),
    "1": Fan(speed=2200.0, state_fail=False),
    "2": Fan(speed=2300.0, state_fail=False),
    "3": Fan(speed=2300.0, state_fail=False),
}

_SectionCpuFail = {
    "CPU": Fan(speed=1000.0, state_fail=True),
    "1": Fan(speed=2200.0, state_fail=False),
    "2": Fan(speed=2300.0, state_fail=False),
    "3": Fan(speed=2300.0, state_fail=False),
}


@pytest.mark.parametrize(
    "test_stringtable, expected_section",
    [
        pytest.param(
            [["1000", "2200", "2300", "2300", "0", "0"]],
            _SectionOk,
            id="everything OK",
        ),
        pytest.param(
            [["1000", "2200", "2300", "2300", "1", "0"]],
            _SectionCpuFail,
            id="CPU not OK",
        ),
    ],
)
def test_parse(test_stringtable: StringTable, expected_section: _Section) -> None:
    assert expected_section == parse(test_stringtable)


def test_discover() -> None:
    assert list(discover(section=_SectionOk)) == [
        Service(item="CPU"),
        Service(item="1"),
        Service(item="2"),
        Service(item="3"),
    ]


@pytest.mark.parametrize(
    "test_item, test_section, expected_result",
    [
        pytest.param(
            "1",
            _SectionOk,
            [
                Result(state=State.OK, summary="Speed: 2200 RPM"),
                Metric("fan", 2200.0),
            ],
            id="everything OK",
        ),
        pytest.param(
            "CPU",
            _SectionCpuFail,
            [
                Result(state=State.CRIT, summary="Status CPU fan not OK"),
                Result(state=State.OK, summary="Speed: 1000 RPM"),
                Metric("fan", 1000.0),
            ],
            id="CPU not OK",
        ),
    ],
)
def test_check(test_item: str, test_section: _Section, expected_result: CheckResult) -> None:
    assert expected_result == list(
        check(
            item=test_item,
            params={"levels": (0.0, 0.0), "output_metrics": True},
            section=test_section,
        )
    )

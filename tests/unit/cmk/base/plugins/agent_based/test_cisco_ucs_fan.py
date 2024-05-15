#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.cisco_ucs_fan import (
    check_cisco_ucs_fan,
    discover_cisco_ucs_fan,
    parse_cisco_ucs_fan,
)

from cmk.plugins.lib.cisco_ucs import Operability


@pytest.fixture(name="section", scope="module")
def fixture_section() -> dict[str, Operability]:
    return parse_cisco_ucs_fan(
        [
            ["sys/rack-unit-1/fan-module-1-1/fan-1", "1"],
            ["sys/rack-unit-1/fan-module-1-1/fan-2", "1"],
            ["sys/rack-unit-1/fan-module-1-2/fan-1", "1"],
            ["sys/rack-unit-1/fan-module-1-2/fan-2", "1"],
            ["sys/rack-unit-1/fan-module-1-3/fan-1", "1"],
            ["sys/rack-unit-1/fan-module-1-3/fan-2", "1"],
            ["sys/rack-unit-1/fan-module-1-4/fan-1", "1"],
            ["sys/rack-unit-1/fan-module-1-4/fan-2", "1"],
            ["sys/rack-unit-1/fan-module-1-5/fan-1", "1"],
            ["sys/rack-unit-1/fan-module-1-5/fan-2", "1"],
            ["sys/rack-unit-1/fan-module-1-6/fan-1", "1"],
            ["sys/rack-unit-1/fan-module-1-6/fan-2", "1"],
            ["sys/rack-unit-1/fan-module-1-7/fan-1", "1"],
            ["sys/rack-unit-1/fan-module-1-7/fan-2", "1"],
        ]
    )


def test_discover_cisco_ucs_mem(section: Mapping[str, Operability]) -> None:
    assert list(discover_cisco_ucs_fan(section)) == [
        Service(item="fan-module-1-1 fan-1"),
        Service(item="fan-module-1-1 fan-2"),
        Service(item="fan-module-1-2 fan-1"),
        Service(item="fan-module-1-2 fan-2"),
        Service(item="fan-module-1-3 fan-1"),
        Service(item="fan-module-1-3 fan-2"),
        Service(item="fan-module-1-4 fan-1"),
        Service(item="fan-module-1-4 fan-2"),
        Service(item="fan-module-1-5 fan-1"),
        Service(item="fan-module-1-5 fan-2"),
        Service(item="fan-module-1-6 fan-1"),
        Service(item="fan-module-1-6 fan-2"),
        Service(item="fan-module-1-7 fan-1"),
        Service(item="fan-module-1-7 fan-2"),
    ]


@pytest.mark.parametrize(
    "item, expected_output",
    [
        pytest.param("missing", [], id="Item missing in data"),
        pytest.param(
            "fan-module-1-7 fan-2",
            [Result(state=State.OK, summary="Status: operable")],
            id="Last item in data",
        ),
    ],
)
def test_check_cisco_ucs_mem(
    section: Mapping[str, Operability], item: str, expected_output: CheckResult
) -> None:
    assert list(check_cisco_ucs_fan(item, section)) == expected_output

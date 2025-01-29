#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v1 import Service
from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Metric, Result, State, StringTable
from cmk.plugins.collection.agent_based.pse_poe import (
    check_pse_poe,
    discover_pse_poe,
    parse_pse_poe,
    Section,
)
from cmk.plugins.lib.poe import PoeStatus, PoeValues

info = [
    ["1", "420", "1", "83"],
    ["2", "420", "1", "380"],
    ["3", "420", "1", "419"],
    ["4", "0", "2", "0"],
    ["5", "0", "3", "0"],
    ["6", "-1", "1", "-1"],
]


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param(
            [
                ["1", "420", "1", "83"],
                ["2", "420", "1", "380"],
                ["3", "420", "1", "419"],
                ["6", "-1", "1", "-1"],
            ],
            {
                "1": PoeValues(
                    poe_max=420, poe_used=83, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
                "2": PoeValues(
                    poe_max=420, poe_used=380, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
                "3": PoeValues(
                    poe_max=420, poe_used=419, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
                "6": PoeValues(
                    poe_max=-1, poe_used=-1, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
            },
            id="on",
        ),
        pytest.param(
            [["4", "0", "2", "0"]],
            {
                "4": PoeValues(
                    poe_max=0, poe_used=0, poe_status=PoeStatus.OFF, poe_status_detail=None
                )
            },
            id="off",
        ),
        pytest.param(
            [["5", "0", "3", "0"]],
            {
                "5": PoeValues(
                    poe_max=0, poe_used=0, poe_status=PoeStatus.FAULTY, poe_status_detail=None
                ),
            },
            id="faulty",
        ),
        pytest.param(
            [["5", "0", "", "0"]],
            {},
            id="missing oid",
        ),
    ],
)
def test_parse_pse_poe(string_table: StringTable, expected: Section) -> None:
    assert parse_pse_poe(string_table) == expected


@pytest.mark.parametrize(
    "section, expected",
    [
        pytest.param(
            {
                "1": PoeValues(
                    poe_max=420, poe_used=83, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
                "2": PoeValues(
                    poe_max=420, poe_used=380, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
                "3": PoeValues(
                    poe_max=420, poe_used=419, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
                "6": PoeValues(
                    poe_max=-1, poe_used=-1, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
            },
            [Service(item="1"), Service(item="2"), Service(item="3"), Service(item="6")],
            id="on",
        ),
        pytest.param(
            {
                "4": PoeValues(
                    poe_max=0, poe_used=0, poe_status=PoeStatus.FAULTY, poe_status_detail=None
                ),
            },
            [Service(item="4")],
        ),
        pytest.param(
            {
                "5": PoeValues(
                    poe_max=0, poe_used=0, poe_status=PoeStatus.FAULTY, poe_status_detail=None
                ),
            },
            [Service(item="5")],
            id="faulty",
        ),
        pytest.param(
            {},
            [],
            id="missing oid",
        ),
    ],
)
def test_discover_pse_poe(section: Section, expected: DiscoveryResult) -> None:
    assert list(discover_pse_poe(section)) == expected


@pytest.mark.parametrize(
    "item, params, section, expected",
    [
        pytest.param(
            "1",
            {"levels": ("fixed", (90.0, 95.0))},
            {
                "1": PoeValues(
                    poe_max=420, poe_used=83, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
            },
            [
                Result(
                    state=State.OK,
                    summary="POE usage (83W/420W): : 19.76%",
                ),
                Metric("power_usage_percentage", 19.761904761904763, levels=(90.0, 95.0)),
            ],
            id="ok",
        ),
        pytest.param(
            "2",
            {"levels": ("fixed", (90.0, 95.0))},
            {
                "2": PoeValues(
                    poe_max=420, poe_used=380, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
            },
            [
                Result(
                    state=State.WARN,
                    summary="POE usage (380W/420W): : 90.48% (warn/crit at 90.00%/95.00%)",
                ),
                Metric("power_usage_percentage", 90.47619047619048, levels=(90.0, 95.0)),
            ],
            id="warn",
        ),
        pytest.param(
            "3",
            {"levels": ("fixed", (90.0, 95.0))},
            {
                "3": PoeValues(
                    poe_max=420, poe_used=419, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
            },
            [
                Result(
                    state=State.CRIT,
                    summary="POE usage (419W/420W): : 99.76% (warn/crit at 90.00%/95.00%)",
                ),
                Metric("power_usage_percentage", 99.76190476190476, levels=(90.0, 95.0)),
            ],
            id="crit",
        ),
        pytest.param(
            "4",
            {"levels": ("fixed", (90.0, 95.0))},
            {
                "4": PoeValues(
                    poe_max=0, poe_used=0, poe_status=PoeStatus.OFF, poe_status_detail=None
                ),
            },
            [
                Result(
                    state=State.OK,
                    summary="Operational status of the PSE is OFF",
                ),
            ],
            id="off",
        ),
        pytest.param(
            "5",
            {"levels": ("fixed", (90.0, 95.0))},
            {
                "5": PoeValues(
                    poe_max=0, poe_used=0, poe_status=PoeStatus.FAULTY, poe_status_detail=None
                ),
            },
            [
                Result(
                    state=State.CRIT,
                    summary="Operational status of the PSE is FAULTY",
                ),
            ],
            id="faulty",
        ),
        pytest.param(
            "6",
            {"levels": ("fixed", (90.0, 95.0))},
            {
                "6": PoeValues(
                    poe_max=-1, poe_used=-1, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
            },
            [
                Result(
                    state=State.UNKNOWN,
                    summary="Device returned faulty data: nominal power: -1, power consumption: -1, operational status: PoeStatus.ON",
                ),
            ],
            id="sanity_check_failed",
        ),
    ],
)
def test_check_pse_poe(
    item: str, params: Mapping[str, Any], section: Section, expected: CheckResult
) -> None:
    assert list(check_pse_poe(item, params, section)) == expected

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.poe import PoeStatus, PoeValues
from cmk.plugins.tplink.agent_based.tplink_poe import (
    check_tplink_poe,
    discover_tplink_poe,
    parse_tplink_poe,
    Section,
)


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param(
            [
                [["49155"], ["49156"], ["49157"], ["49160"]],
                [
                    ["1", "1", "300", "290", "2"],
                    ["2", "1", "300", "36", "2"],
                    ["3", "1", "300", "0", "2"],
                    ["4", "1", "300", "39", "2"],
                ],
            ],
            {
                "49155": PoeValues(
                    poe_max=30.0, poe_used=29.0, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
                "49156": PoeValues(
                    poe_max=30.0, poe_used=3.6, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
                "49157": PoeValues(
                    poe_max=30.0, poe_used=0.0, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
                "49160": PoeValues(
                    poe_max=30.0, poe_used=3.9, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
            },
            id="on",
        ),
        pytest.param(
            [
                [["49153"]],
                [
                    ["1", "1", "300", "0", "1"],
                ],
            ],
            {
                "49153": PoeValues(
                    poe_max=30.0, poe_used=0.0, poe_status=PoeStatus.OFF, poe_status_detail=None
                ),
            },
            id="turning-on",
        ),
        pytest.param(
            [
                [["1"], ["49154"]],
                [
                    ["1", "1", "300", "0", "0"],
                    ["2", "1", "300", "-10", "0"],
                ],
            ],
            {
                "1": PoeValues(
                    poe_max=30.0, poe_used=0.0, poe_status=PoeStatus.OFF, poe_status_detail=None
                ),
                "49154": PoeValues(
                    poe_max=30.0, poe_used=-1.0, poe_status=PoeStatus.OFF, poe_status_detail=None
                ),
            },
            id="off",
        ),
        pytest.param(
            [
                [["49159"], ["49180"]],
                [["1", "1", "300", "0", "8"], ["2", "1", "300", "0", "10"]],
            ],
            {
                "49159": PoeValues(
                    poe_max=30.0,
                    poe_used=0.0,
                    poe_status=PoeStatus.FAULTY,
                    poe_status_detail="hardware-fault",
                ),
                "49180": PoeValues(
                    poe_max=30.0, poe_used=0.0, poe_status=PoeStatus.FAULTY, poe_status_detail=None
                ),
            },
            id="faulty",
        ),
    ],
)
def test_parse_tplink_poe(string_table: Sequence[StringTable], expected: Section) -> None:
    assert parse_tplink_poe(string_table) == expected


@pytest.mark.parametrize(
    "section, expected",
    [
        pytest.param(
            {
                "49156": PoeValues(
                    poe_max=30.0, poe_used=3.6, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
                "49157": PoeValues(
                    poe_max=30.0, poe_used=0.0, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
                "49160": PoeValues(
                    poe_max=30.0, poe_used=3.9, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
            },
            [Service(item="49156"), Service(item="49157"), Service(item="49160")],
        ),
        pytest.param(
            {
                "1": PoeValues(
                    poe_max=30.0, poe_used=0.0, poe_status=PoeStatus.OFF, poe_status_detail=None
                ),
                "49153": PoeValues(
                    poe_max=30.0, poe_used=0.0, poe_status=PoeStatus.OFF, poe_status_detail=None
                ),
                "49154": PoeValues(
                    poe_max=30.0, poe_used=-1.0, poe_status=PoeStatus.OFF, poe_status_detail=None
                ),
            },
            [Service(item="1"), Service(item="49153"), Service(item="49154")],
            id="off",
        ),
        pytest.param(
            {
                "49159": PoeValues(
                    poe_max=30.0,
                    poe_used=0.0,
                    poe_status=PoeStatus.FAULTY,
                    poe_status_detail="hardware-fault",
                ),
                "49180": PoeValues(
                    poe_max=30.0, poe_used=0.0, poe_status=PoeStatus.FAULTY, poe_status_detail=None
                ),
            },
            [Service(item="49159"), Service(item="49180")],
            id="faulty",
        ),
    ],
)
def test_discover_tplink_poe(section: Section, expected: DiscoveryResult) -> None:
    assert list(discover_tplink_poe(section)) == expected


@pytest.mark.parametrize(
    "item, params, section, expected",
    [
        pytest.param(
            "1",
            {},
            {
                "1": PoeValues(
                    poe_max=30.0, poe_used=0.0, poe_status=PoeStatus.OFF, poe_status_detail=None
                ),
            },
            [Result(state=State.OK, summary="Operational status of the PSE is OFF")],
            id="off",
        ),
        pytest.param(
            "49153",
            {},
            {
                "49153": PoeValues(
                    poe_max=30.0, poe_used=0.0, poe_status=PoeStatus.OFF, poe_status_detail=None
                ),
            },
            [Result(state=State.OK, summary="Operational status of the PSE is OFF")],
            id="turning-on",
        ),
        pytest.param(
            "49154",
            {},
            {
                "49154": PoeValues(
                    poe_max=30.0, poe_used=-1.0, poe_status=PoeStatus.OFF, poe_status_detail=None
                )
            },
            [
                Result(
                    state=State.UNKNOWN,
                    summary="Device returned faulty data: nominal power: 30.0, power consumption: -1.0, operational status: PoeStatus.OFF",
                ),
            ],
            id="sanity_check_failed",
        ),
        pytest.param(
            "49155",
            {},
            {
                "49155": PoeValues(
                    poe_max=30.0, poe_used=29.0, poe_status=PoeStatus.ON, poe_status_detail=None
                )
            },
            [
                Result(
                    state=State.CRIT,
                    summary="POE usage (29.0W/30.0W): : 96.67% (warn/crit at 90.00%/95.00%)",
                ),
                Metric("power_usage_percentage", 96.66666666666667, levels=(90.0, 95.0)),
            ],
            id="crit",
        ),
        pytest.param(
            "49156",
            {},
            {
                "49156": PoeValues(
                    poe_max=30.0, poe_used=3.6, poe_status=PoeStatus.ON, poe_status_detail=None
                ),
            },
            [
                Result(state=State.OK, summary="POE usage (3.6W/30.0W): : 12.00%"),
                Metric(
                    "power_usage_percentage",
                    12.000000000000002,
                    levels=(90.0, 95.0),
                ),
            ],
            id="ok",
        ),
        pytest.param(
            "49180",
            {},
            {
                "49180": PoeValues(
                    poe_max=30.0, poe_used=0.0, poe_status=PoeStatus.FAULTY, poe_status_detail=None
                )
            },
            [Result(state=State.CRIT, summary="Operational status of the PSE is FAULTY")],
            id="faulty",
        ),
        pytest.param(
            "49159",
            {},
            {
                "49159": PoeValues(
                    poe_max=30.0,
                    poe_used=0.0,
                    poe_status=PoeStatus.FAULTY,
                    poe_status_detail="hardware-fault",
                )
            },
            [
                Result(
                    state=State.CRIT,
                    summary="Operational status of the PSE is FAULTY (hardware-fault)",
                )
            ],
            id="faulty_details",
        ),
    ],
)
def test_check_tplink_poe(
    item: str, params: Mapping[str, Any], section: Section, expected: CheckResult
) -> None:
    assert list(check_tplink_poe(item, params, section)) == expected

#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.apc_netbotz_fluid import (
    check_apc_netbotz_fluid,
    CheckResult,
    discover_apc_netbotz_fluid,
    DiscoveryResult,
    FluidSensorSection,
    FluidSensorState,
    parse_apc_netbotz_fluid,
)

TEST_SECTION = [
    ["0", "3", "Banana1", "1"],
    ["22", "44", "Banana2", "2"],
    ["33", "99", "Banana3", "3"],
]

PARSED_SECTION = {
    "Banana1 0/3": FluidSensorState.FLUIDLEAK,
    "Banana2 22/44": FluidSensorState.NOFLUID,
    "Banana3 33/99": FluidSensorState.UNKNOWN,
}


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param(
            [
                ["0", "3", "Banana", "1"],
            ],
            {
                "Banana 0/3": FluidSensorState.FLUIDLEAK,
            },
            id="leak",
        ),
        pytest.param(
            [
                ["1", "4", "Banana", "2"],
            ],
            {
                "Banana 1/4": FluidSensorState.NOFLUID,
            },
            id="noleak",
        ),
        pytest.param(
            [
                ["2", "5", "Banana", "3"],
            ],
            {
                "Banana 2/5": FluidSensorState.UNKNOWN,
            },
            id="unknown",
        ),
        pytest.param(
            TEST_SECTION,
            PARSED_SECTION,
            id="all",
        ),
    ],
)
def test_parse_apc_netbotz_fluid(
    string_table: StringTable, expected_result: FluidSensorSection
) -> None:

    assert parse_apc_netbotz_fluid(string_table) == expected_result


@pytest.mark.parametrize(
    "section, discovered",
    [
        pytest.param(
            PARSED_SECTION,
            [
                Service(item="Banana1 0/3"),
                Service(item="Banana2 22/44"),
                Service(item="Banana3 33/99"),
            ],
            id="several discovered",
        ),
    ],
)
def test_discovery_apc_netbotz_fluid(
    section: FluidSensorSection, discovered: DiscoveryResult
) -> None:

    assert list(discover_apc_netbotz_fluid(section)) == discovered


@pytest.mark.parametrize(
    "item, section, result",
    [
        pytest.param(
            "Banana1 0/3",
            PARSED_SECTION,
            [
                Result(
                    state=State.CRIT,
                    summary="Leak detected",
                ),
            ],
            id="crit",
        ),
        pytest.param(
            "Banana2 22/44",
            PARSED_SECTION,
            [
                Result(
                    state=State.OK,
                    summary="No leak detected",
                ),
            ],
            id="ok",
        ),
        pytest.param(
            "Banana3 33/99",
            PARSED_SECTION,
            [
                Result(
                    state=State.UNKNOWN,
                    summary="State Unknown",
                ),
            ],
            id="unknown",
        ),
        pytest.param(
            "non_existent_item",
            PARSED_SECTION,
            [],
            id="unknown",
        ),
    ],
)
def test_check_apc_netbotz_fluid(
    item: str, section: FluidSensorSection, result: CheckResult
) -> None:

    assert list(check_apc_netbotz_fluid(item, section)) == result

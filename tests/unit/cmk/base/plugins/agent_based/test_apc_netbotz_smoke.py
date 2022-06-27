#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.apc_netbotz_smoke import (
    check_apc_netbotz_smoke,
    CheckResult,
    discover_apc_netbotz_smoke,
    DiscoveryResult,
    parse_apc_netbotz_smoke,
    SmokeSensorSection,
    SmokeSensorState,
)

TEST_SECTION = [
    ["0", "3", "Banana1", "1"],
    ["1", "4", "Banana2", "2"],
    ["2", "5", "Banana3", "3"],
]

PARSED_SECTION = {
    "Banana1 0/3": SmokeSensorState.SMOKEDETECTED,
    "Banana2 1/4": SmokeSensorState.NOSMOKE,
    "Banana3 2/5": SmokeSensorState.UNKNOWN,
}


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param(
            [
                ["0", "3", "Banana", "1"],
            ],
            {
                "Banana 0/3": SmokeSensorState.SMOKEDETECTED,
            },
            id="smoke",
        ),
        pytest.param(
            [
                ["1", "4", "Banana", "2"],
            ],
            {
                "Banana 1/4": SmokeSensorState.NOSMOKE,
            },
            id="nosmoke",
        ),
        pytest.param(
            [
                ["2", "5", "Banana", "3"],
            ],
            {
                "Banana 2/5": SmokeSensorState.UNKNOWN,
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
def test_parse_apc_netbotz_smoke(
    string_table: StringTable, expected_result: SmokeSensorSection
) -> None:

    assert parse_apc_netbotz_smoke(string_table) == expected_result


@pytest.mark.parametrize(
    "section, discovered",
    [
        pytest.param(
            PARSED_SECTION,
            [
                Service(item="Banana1 0/3"),
                Service(item="Banana2 1/4"),
                Service(item="Banana3 2/5"),
            ],
            id="several discovered",
        ),
    ],
)
def test_discovery_apc_netbotz_smoke(
    section: SmokeSensorSection, discovered: DiscoveryResult
) -> None:

    assert list(discover_apc_netbotz_smoke(section)) == discovered


@pytest.mark.parametrize(
    "item, section, result",
    [
        pytest.param(
            "Banana1 0/3",
            PARSED_SECTION,
            [
                Result(
                    state=State.CRIT,
                    summary="Smoke detected",
                ),
            ],
            id="crit",
        ),
        pytest.param(
            "Banana2 1/4",
            PARSED_SECTION,
            [
                Result(
                    state=State.OK,
                    summary="No smoke detected",
                ),
            ],
            id="ok",
        ),
        pytest.param(
            "Banana3 2/5",
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
def test_check_apc_netbotz_smoke(
    item: str, section: SmokeSensorSection, result: CheckResult
) -> None:

    assert list(check_apc_netbotz_smoke(item, section)) == result

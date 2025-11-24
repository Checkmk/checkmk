#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.cisco_meraki.agent_based.cisco_meraki_org_appliance_performance import (
    check_appliance_performance,
    CheckParams,
    discover_appliance_performance,
    parse_appliance_performance,
)


@pytest.mark.parametrize("string_table", [[], [[]], [[""]]])
def test_discover_appliance_performance_no_payload(string_table: StringTable) -> None:
    section = parse_appliance_performance(string_table)
    assert not list(discover_appliance_performance(section))


def test_discover_appliance_performance() -> None:
    string_table = [[f"[{json.dumps({'perfScore': '20.0'})}]"]]
    section = parse_appliance_performance(string_table)

    value = list(discover_appliance_performance(section))
    expected = [Service()]

    assert value == expected


@pytest.mark.parametrize("string_table", [[], [[]], [[""]]])
def test_check_appliance_uplinks_no_payload(string_table: StringTable, params: CheckParams) -> None:
    section = parse_appliance_performance(string_table)
    assert not list(check_appliance_performance(params, section))


@pytest.fixture
def params() -> CheckParams:
    return CheckParams(levels_upper=("fixed", (60, 80)))


@pytest.mark.parametrize(
    "performance, state, summary",
    [
        (50.0, State.OK, "Utilization: 50.00%"),
        (70.0, State.WARN, "Utilization: 70.00% (warn/crit at 60.00%/80.00%)"),
        (90.0, State.CRIT, "Utilization: 90.00% (warn/crit at 60.00%/80.00%)"),
    ],
)
def test_check_appliance_uplinks(
    performance: float, state: State, summary: str, params: CheckParams
) -> None:
    string_table = [[f"[{json.dumps({'perfScore': performance})}]"]]
    section = parse_appliance_performance(string_table)

    value = list(check_appliance_performance(params, section))
    expected = [
        Result(state=state, summary=summary),
        Metric("utilization", performance, levels=(60.0, 80.0), boundaries=(0.0, 100.0)),
    ]

    assert value == expected

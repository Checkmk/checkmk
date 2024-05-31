#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
from collections.abc import Mapping, Sequence
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.extreme_vsp_switches_cpu_util import (
    check_vsp_switches_cpu_util,
    discover_vsp_switches_cpu_util,
    parse_vsp_switches_cpu_util,
)

_STRING_TABLE = [["8"]]


@pytest.mark.parametrize(
    "string_table, expected_discovery_result",
    [
        pytest.param(
            _STRING_TABLE,
            [Service()],
            id="A service is created if the information about the CPU Utilization is available.",
        ),
        pytest.param(
            [],
            [],
            id="If there is no information, no Services are created.",
        ),
    ],
)
def test_discover_vsp_switches_cpu_util(
    string_table: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert (
        list(discover_vsp_switches_cpu_util(parse_vsp_switches_cpu_util(string_table)))
        == expected_discovery_result
    )


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "string_table, params, expected_check_result",
    [
        pytest.param(
            _STRING_TABLE,
            {"util": (80.0, 90.0)},
            [
                Result(state=State.OK, summary="Total CPU: 8.00%"),
                Metric("util", 8.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
            ],
            id="The CPU Utilization is below the WARN/CRIT levels, so the check state is OK.",
        ),
        pytest.param(
            [["85"]],
            {"util": (80.0, 90.0)},
            [
                Result(state=State.WARN, summary="Total CPU: 85.00% (warn/crit at 80.00%/90.00%)"),
                Metric("util", 85.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
            ],
            id="The CPU Utilization is above the WARN level, so the check state is WARN.",
        ),
        pytest.param(
            [["95"]],
            {"util": (80.0, 90.0)},
            [
                Result(state=State.CRIT, summary="Total CPU: 95.00% (warn/crit at 80.00%/90.00%)"),
                Metric("util", 95.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
            ],
            id="The CPU Utilization is above the CRIT level, so the check state is CRIT.",
        ),
    ],
)
def test_check_vsp_switches_cpu_util(
    string_table: StringTable,
    params: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    with time_machine.travel(datetime.datetime(2023, 1, 30, 12, tzinfo=ZoneInfo("UTC"))):
        assert (
            list(
                check_vsp_switches_cpu_util(
                    params=params,
                    section=parse_vsp_switches_cpu_util(string_table),
                )
            )
            == expected_check_result
        )

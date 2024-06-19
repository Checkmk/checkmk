#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from cmk.plugins.lib import akcp_sensor

STRING_TABLE_1 = [["Dual Humidity Port 1", "30", "7", "1"]]
STRING_TABLE_2 = [["Humidity1 Description", "", "7", "1"], ["Humidity2 Description", "", "0", "2"]]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            STRING_TABLE_1,
            [Service(item="Dual Humidity Port 1")],
        ),
        (
            STRING_TABLE_2,
            [Service(item="Humidity1 Description")],
        ),
    ],
)
def test_akcp_humidity_discover(
    string_table: StringTable, expected_result: DiscoveryResult
) -> None:
    assert (
        list(akcp_sensor.inventory_akcp_humidity(akcp_sensor.parse_akcp_sensor(string_table)))
        == expected_result
    )


@pytest.mark.parametrize(
    "string_table, item, expected_result",
    [
        (
            STRING_TABLE_1,
            "Dual Humidity Port 1",
            [
                Result(state=State.CRIT, summary="State: sensor error"),
                Result(state=State.CRIT, summary="30.00% (warn/crit below 30.00%/35.00%)"),
                Metric("humidity", 30.0, levels=(60.0, 65.0), boundaries=(0.0, 100.0)),
            ],
        ),
        (
            STRING_TABLE_2,
            "Humidity1 Description",
            [Result(state=State.CRIT, summary="State: sensor error")],
        ),
    ],
)
def test_akcp_humidity_check(
    string_table: StringTable, item: str, expected_result: CheckResult
) -> None:
    assert (
        list(
            akcp_sensor.check_akcp_humidity(
                item,
                akcp_sensor.AKCP_HUMIDITY_CHECK_DEFAULT_PARAMETERS,
                akcp_sensor.parse_akcp_sensor(string_table),
            )
        )
        == expected_result
    )

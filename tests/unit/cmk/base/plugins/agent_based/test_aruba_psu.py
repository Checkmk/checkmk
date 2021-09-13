#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import aruba_psu
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

DATA = [
    ["1", "3", "0", "24", "AC 120V/240V", "16", "680", "744952", "JL086A"],
    ["2", "4", "0", "27", "AC 120V/240V", "20", "680", "744952", "JL086A"],
    ["3", "5", "0", "51", "AC 120V/240V", "570", "680", "1811404", "JL086A"],
    ["4", "6", "1", "61", "AC 120V/240V", "620", "680", "745051", "JL086A"],
    ["5", "1", "0", "0", "-- ---------", "0", "0", "0", ""],
    ["6", "2", "0", "0", "-- ---------", "0", "0", "0", ""],
]


@pytest.mark.parametrize(
    "string_table, result",
    [
        (
            DATA,
            [
                Service(item="JL086A 1"),
                Service(item="JL086A 2"),
                Service(item="JL086A 3"),
                Service(item="JL086A 4"),
            ],
        ),
    ],
)
def test_discover_aruba_psu_status(
    string_table: StringTable,
    result: DiscoveryResult,
):
    section = aruba_psu.parse_aruba_psu(string_table)
    assert list(aruba_psu.discover_aruba_psu(section)) == result


@pytest.mark.parametrize(
    "string_table, item, result",
    [
        (
            DATA,
            "JL086A 1",
            [
                Result(state=State.OK, summary="PSU Status: Powered"),
                Result(state=State.OK, summary="Uptime: 8 days 14 hours"),
            ],
        ),
        (
            DATA,
            "JL086A 2",
            [
                Result(state=State.CRIT, summary="PSU Status: Failed"),
                Result(state=State.OK, summary="Uptime: 8 days 14 hours"),
            ],
        ),
        (
            DATA,
            "JL086A 3",
            [
                Result(state=State.CRIT, summary="PSU Status: PermFailure"),
                Result(state=State.OK, summary="Uptime: 20 days 23 hours"),
            ],
        ),
        (
            DATA,
            "JL086A 4",
            [
                Result(state=State.OK, summary="PSU Status: Max"),
                Result(state=State.OK, summary="Uptime: 8 days 14 hours"),
            ],
        ),
    ],
)
def test_check_aruba_psu_status(
    string_table: StringTable,
    item: str,
    result: CheckResult,
):
    section = aruba_psu.parse_aruba_psu(string_table)
    assert list(aruba_psu.check_aruba_psu_status(item, section)) == result


@pytest.mark.parametrize(
    "string_table, item, result",
    [
        (
            DATA,
            "JL086A 1",
            [
                Metric("temp", 24.0, levels=(50.0, 60.0)),
                Result(state=State.OK, summary="Temperature: 24.0°C"),
                Result(state=State.OK, notice="Configuration: only use user levels"),
            ],
        ),
        (
            DATA,
            "JL086A 2",
            [
                Metric("temp", 27.0, levels=(50.0, 60.0)),
                Result(state=State.OK, summary="Temperature: 27.0°C"),
                Result(state=State.OK, notice="Configuration: only use user levels"),
            ],
        ),
        (
            DATA,
            "JL086A 3",
            [
                Metric("temp", 51.0, levels=(50.0, 60.0)),
                Result(
                    state=State.WARN, summary="Temperature: 51.0°C (warn/crit at 50.0°C/60.0°C)"
                ),
                Result(state=State.OK, notice="Configuration: only use user levels"),
            ],
        ),
        (
            DATA,
            "JL086A 4",
            [
                Metric("temp", 61.0, levels=(50.0, 60.0)),
                Result(
                    state=State.CRIT, summary="Temperature: 61.0°C (warn/crit at 50.0°C/60.0°C)"
                ),
                Result(state=State.OK, notice="Configuration: only use user levels"),
            ],
        ),
    ],
)
def test_check_aruba_psu_temp(
    string_table: StringTable,
    item: str,
    result: CheckResult,
):
    section = aruba_psu.parse_aruba_psu(string_table)
    assert (
        list(
            aruba_psu.check_aruba_psu_temp(
                item,
                aruba_psu.default_psu_temperature_parameters,
                section,
            )
        )
        == result
    )


@pytest.mark.parametrize(
    "string_table, item, result",
    [
        (
            DATA,
            "JL086A 1",
            [
                Result(state=State.OK, summary="Wattage: 16.00W"),
                Metric("power", 16.0, levels=(500.0, 600.0)),
                Result(state=State.OK, notice="Wattage: 2.35%"),
                Result(state=State.OK, summary="Maximum Wattage: 680.00W"),
                Result(state=State.OK, notice="Voltage Info: AC 120V/240V"),
            ],
        ),
        (
            DATA,
            "JL086A 2",
            [
                Result(state=State.OK, summary="Wattage: 20.00W"),
                Metric("power", 20.0, levels=(500.0, 600.0)),
                Result(state=State.OK, notice="Wattage: 2.94%"),
                Result(state=State.OK, summary="Maximum Wattage: 680.00W"),
                Result(state=State.OK, notice="Voltage Info: AC 120V/240V"),
            ],
        ),
        (
            DATA,
            "JL086A 3",
            [
                Result(state=State.WARN, summary="Wattage: 570.00W (warn/crit at 500.00W/600.00W)"),
                Metric("power", 570.0, levels=(500.0, 600.0)),
                Result(state=State.WARN, summary="Wattage: 83.82% (warn/crit at 80.00%/90.00%)"),
                Result(state=State.OK, summary="Maximum Wattage: 680.00W"),
                Result(state=State.OK, notice="Voltage Info: AC 120V/240V"),
            ],
        ),
        (
            DATA,
            "JL086A 4",
            [
                Result(state=State.CRIT, summary="Wattage: 620.00W (warn/crit at 500.00W/600.00W)"),
                Metric("power", 620.0, levels=(500.0, 600.0)),
                Result(state=State.CRIT, summary="Wattage: 91.18% (warn/crit at 80.00%/90.00%)"),
                Result(state=State.OK, summary="Maximum Wattage: 680.00W"),
                Result(state=State.OK, notice="Voltage Info: AC 120V/240V"),
            ],
        ),
    ],
)
def test_check_aruba_psu_wattage(
    string_table: StringTable,
    item: str,
    result: CheckResult,
):
    section = aruba_psu.parse_aruba_psu(string_table)
    assert (
        list(
            aruba_psu.check_aruba_psu_wattage(
                item,
                aruba_psu.default_psu_wattage_parameters,
                section,
            )
        )
        == result
    )

#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.lib.temperature import TempParamDict
from cmk.plugins.netapp.agent_based.netapp_ontap_temp import (
    _check_netapp_ontap_temp,
    discovery_netapp_ontap_temp,
)
from cmk.plugins.netapp.models import ShelfTemperatureModel


class ShelfTemperatureModelFactory(ModelFactory):
    __model__ = ShelfTemperatureModel


SENSORS_SECTION = {
    "Ambient Shelf 2": [
        ShelfTemperatureModelFactory.build(
            list_id="2",
            state="ok",
            id=111,
            temperature=20.0,
            ambient=True,
            low_warning=None,
            low_critical=None,
            high_warning=None,
            high_critical=None,
        ),
    ],
    "Internal Shelf 2": [
        ShelfTemperatureModelFactory.build(
            list_id="2",
            state="ok",
            temperature=50.0,
            ambient=False,
            low_warning=None,
            low_critical=None,
            high_warning=None,
            high_critical=None,
        ),
    ],
    "Ambient Shelf 1": [
        ShelfTemperatureModelFactory.build(
            list_id="1",
            state="ok",
            temperature=50.0,
            ambient=True,
            low_warning=None,
            low_critical=None,
            high_warning=None,
            high_critical=None,
        ),
        ShelfTemperatureModelFactory.build(
            list_id="1",
            state="ok",
            temperature=10.0,
            ambient=True,
            low_warning=None,
            low_critical=None,
            high_warning=None,
            high_critical=None,
        ),
        ShelfTemperatureModelFactory.build(
            list_id="1",
            state="ok",
            temperature=20.0,
            ambient=True,
            low_warning=None,
            low_critical=None,
            high_warning=None,
            high_critical=None,
        ),
        ShelfTemperatureModelFactory.build(
            list_id="1",
            id=20,
            state="error",
            temperature=None,
            ambient=True,
            low_warning=None,
            low_critical=None,
            high_warning=None,
            high_critical=None,
        ),
    ],
    "Internal Shelf 1": [
        ShelfTemperatureModelFactory.build(
            list_id="1",
            state="ok",
            temperature=30.0,
            ambient=False,
            low_warning=None,
            low_critical=None,
            high_warning=None,
            high_critical=None,
        ),
    ],
}


def test_discovery_netapp_ontap_temp() -> None:
    result = list(discovery_netapp_ontap_temp(section=SENSORS_SECTION))

    assert all(
        el
        in [
            Service(item="Internal Shelf 2"),
            Service(item="Ambient Shelf 2"),
            Service(item="Internal Shelf 1"),
            Service(item="Ambient Shelf 1"),
        ]
        for el in result
    )


NOW_SIMULATED_SECONDS = 0
FIVE_MIN_AGO_SIMULATED_SECONDS = -300


def test_check_netapp_ontap_temp_() -> None:
    result = list(
        _check_netapp_ontap_temp(
            item="Ambient Shelf 1", params={}, section=SENSORS_SECTION, value_store={}
        )
    )

    assert result == [
        Result(state=State.OK, summary="Sensors: 3"),
        Result(state=State.OK, summary="Highest: 50 °C"),
        Metric("temp", 50.0),
        Result(state=State.OK, summary="Average: 26.7 °C"),
        Result(state=State.OK, summary="Lowest: 10 °C"),
        Result(state=State.CRIT, summary="Additional failed sensors: 1 (1/20)"),
    ]


@pytest.mark.parametrize(
    "params, expected_trend_result",
    [
        pytest.param(
            TempParamDict(
                input_unit="c",
                output_unit="c",
                trend_compute={
                    "period": 5,
                    "trend_levels": (5, 10),
                    "trend_levels_lower": (5, 10),
                    "trend_timeleft": (240, 120),
                },
            ),
            Result(
                state=State.CRIT,
                summary="Temperature trend: +20.0 °C per 5 min (warn/crit at +5 °C per 5 min/+10 °C per 5 min)",
            ),
            id="trend result crit",
        ),
        pytest.param(
            TempParamDict(
                input_unit="c",
                output_unit="c",
                trend_compute={
                    "period": 5,
                    "trend_levels": (50, 100),
                    "trend_levels_lower": (5, 10),
                    "trend_timeleft": (240, 120),
                },
            ),
            Result(
                state=State.OK,
                summary="Temperature trend: +20.0 °C per 5 min",
            ),
            id="trend result OK",
        ),
    ],
)
def test_check_netapp_ontap_temp_trend(
    params: TempParamDict, expected_trend_result: Result
) -> None:
    value_store = {
        "temp.2/111.delta": (
            FIVE_MIN_AGO_SIMULATED_SECONDS,
            0.0,
        ),
        "temp.2/111.dev.delta": (
            FIVE_MIN_AGO_SIMULATED_SECONDS,
            0.0,
        ),
        "temp.overall_trend.delta": (
            FIVE_MIN_AGO_SIMULATED_SECONDS,
            0.0,
        ),
        "temp.overall_trend.dev.delta": (
            FIVE_MIN_AGO_SIMULATED_SECONDS,
            0.0,
        ),
    }

    with time_machine.travel(datetime.fromtimestamp(NOW_SIMULATED_SECONDS, tz=ZoneInfo("UTC"))):
        result = list(
            _check_netapp_ontap_temp(
                item="Ambient Shelf 2",
                params=params,
                section=SENSORS_SECTION,
                value_store=value_store,
            )
        )

        assert result[-1] == expected_trend_result

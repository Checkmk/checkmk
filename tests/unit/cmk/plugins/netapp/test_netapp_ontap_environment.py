#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json

import pytest
import time_machine
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.lib.temperature import TempParamDict
from cmk.plugins.netapp.agent_based.netapp_ontap_environment import (
    check_environment_threshold,
    check_netapp_ontap_environment_discrete,
    discover_netapp_ontap_environment,
    parse_netapp_ontap_environment,
)
from cmk.plugins.netapp.models import (
    EnvironmentDiscreteSensorModel,
    EnvironmentThresholdSensorModel,
)


class EnvironmentDiscreteSensorModelFactory(ModelFactory):
    __model__ = EnvironmentDiscreteSensorModel


class EnvironmentThresholdSensorModelFactory(ModelFactory):
    __model__ = EnvironmentThresholdSensorModel


def test_parse_netapp_ontap_environment() -> None:
    string_table_dict = [
        {
            "name": "CPU1 DTS Temp",
            "node_name": "mcc_darz_a-02",
            "sensor_type": "thermal",
            "threshold_state": "normal",
            "value": -58,
            "value_units": "C",
        },
        {
            "discrete_state": "normal",
            "discrete_value": "OK",
            "name": "NAND Status",
            "node_name": "mcc_darz_a-02",
            "sensor_type": "discrete",
        },
        {
            "discrete_state": "not_available",
            "name": "NAND Not Available",
            "node_name": "mcc_darz_a-02",
            "sensor_type": "discrete",
        },
    ]

    string_table = [[json.dumps(row)] for row in string_table_dict]

    result = parse_netapp_ontap_environment(section=string_table)
    expected_types = [
        EnvironmentThresholdSensorModel,
        EnvironmentDiscreteSensorModel,
    ]

    assert len(result) == 3
    assert all(
        isinstance(el, sensor_type) for el, sensor_type in zip(result.values(), expected_types)
    )


_SENSORS_MODELS = [
    EnvironmentDiscreteSensorModelFactory.build(
        name="discrete_sensor",
        discrete_state="normal",
        discrete_value="OK",
    ),
    EnvironmentDiscreteSensorModelFactory.build(
        name="discrete_sensor_2",
        discrete_state="not_available",
        discrete_value=None,
    ),
    EnvironmentThresholdSensorModelFactory.build(
        name="voltage_sensor",
        sensor_type="voltage",
        value=10000,
        value_units="mV",
        threshold_state="normal",
    ),
    EnvironmentThresholdSensorModelFactory.build(
        name="thermal_sensor",
        sensor_type="thermal",
        value=30,
        value_units="C",
        threshold_state="normal",
        warning_high_threshold=50,
        warning_low_threshold=0,
        critical_high_threshold=90,
        critical_low_threshold=0,
    ),
]


def test_discover_netapp_ontap_environment_with_predicate() -> None:
    section = {model.name: model for model in _SENSORS_MODELS}

    result = discover_netapp_ontap_environment(predicate=lambda v: v.sensor_type == "voltage")(
        section
    )

    assert list(result) == [Service(item="voltage_sensor")]


def test_discover_netapp_ontap_environment_without_predicate() -> None:
    section = {model.name: model for model in _SENSORS_MODELS}

    result = discover_netapp_ontap_environment()(section)

    assert list(result) == [
        Service(item="discrete_sensor"),
        Service(item="discrete_sensor_2"),
        Service(item="voltage_sensor"),
        Service(item="thermal_sensor"),
    ]


@pytest.mark.parametrize(
    "item, expected_result",
    [
        pytest.param(
            "discrete_sensor",
            [Result(state=State.OK, summary="Sensor state: normal, Sensor value: OK")],
            id="sensor status ok",
        ),
        pytest.param(
            "discrete_sensor2",
            [
                Result(
                    state=State.CRIT,
                    summary="Sensor state: failed",
                )
            ],
            id="sensor status crit",
        ),
    ],
)
def test_check_netapp_ontap_environment_discrete(item: str, expected_result: CheckResult) -> None:
    discrete_models = [
        EnvironmentDiscreteSensorModelFactory.build(
            name="discrete_sensor", discrete_state="normal", discrete_value="OK"
        ),
        EnvironmentDiscreteSensorModelFactory.build(
            name="discrete_sensor2",
            discrete_state="failed",
            discrete_value=None,
        ),
    ]

    section = {model.name: model for model in discrete_models}

    result = check_netapp_ontap_environment_discrete(item=item, params=None, section=section)

    assert list(result) == expected_result


NOW_SIMULATED = 0
FIVE_MIN_AGO_SIMULATED = -300


_THRESHOLD_MODELS = [
    EnvironmentThresholdSensorModelFactory.build(
        name="voltage_sensor",
        sensor_type="voltage",
        value=10000,
        value_units="mV",
        threshold_state="normal",
        warning_high_threshold=None,
        warning_low_threshold=None,
        critical_high_threshold=None,
        critical_low_threshold=None,
    ),
    EnvironmentThresholdSensorModelFactory.build(
        name="thermal_sensor",
        sensor_type="thermal",
        value=30,
        value_units="C",
        threshold_state="normal",
        warning_high_threshold=20,
        warning_low_threshold=0,
        critical_high_threshold=90,
        critical_low_threshold=0,
    ),
    EnvironmentThresholdSensorModelFactory.build(
        name="fan_sensor",
        sensor_type="fan",
        value=3000,
        value_units="rpm",
        threshold_state="normal",
        warning_high_threshold=5000,
        critical_high_threshold=9000,
        warning_low_threshold=0,
        critical_low_threshold=0,
    ),
    EnvironmentThresholdSensorModelFactory.build(
        name="fan_sensor_2",
        sensor_type="fan",
        value=None,
        value_units=None,
        threshold_state="not_available",
    ),
]


def test_check_environment_threshold_voltage() -> None:
    section = {model.name: model for model in _THRESHOLD_MODELS}

    result = list(
        check_environment_threshold(
            item="voltage_sensor", params={}, section=section, value_store={}
        )
    )

    assert result == [Result(state=State.OK, summary="10.0 v"), Metric("voltage", 10.0)]


def test_check_environment_threshold_thermal() -> None:
    section = {model.name: model for model in _THRESHOLD_MODELS}

    result = list(
        check_environment_threshold(
            item="thermal_sensor", params={}, section=section, value_store={}
        )
    )

    assert isinstance(result[0], Metric)
    assert result[0].name == "temp" and result[0].value == 30.0

    assert isinstance(result[1], Result)
    assert result[1].state == State.WARN and result[1].summary.startswith("Temperature: 30 °C")


def test_check_environment_threshold_fan() -> None:
    section = {model.name: model for model in _THRESHOLD_MODELS}

    # test ok sensor
    result = list(
        check_environment_threshold(item="fan_sensor", params={}, section=section, value_store={})
    )

    assert result[0] == Result(state=State.OK, summary="3000 rpm")
    assert isinstance(result[1], Metric)
    assert result[1].name == "fan" and result[1].value == 3000.0


def test_check_environment_threshold_fan_non_normal() -> None:
    section = {model.name: model for model in _THRESHOLD_MODELS}

    # test sensor with not-normal state
    result = list(
        check_environment_threshold(item="fan_sensor_2", params={}, section=section, value_store={})
    )

    assert result == [Result(state=State.CRIT, summary="Sensor state: not_available")]


@pytest.mark.parametrize(
    "sensor_model, expected_result",
    [
        pytest.param(
            EnvironmentThresholdSensorModelFactory.build(
                name="thermal_sensor",
                sensor_type="thermal",
                value=10,
                value_units="C",
                threshold_state="normal",
                warning_high_threshold=20,
                warning_low_threshold=0,
                critical_high_threshold=90,
                critical_low_threshold=0,
            ),
            [
                Metric("temp", 10.0, levels=(20.0, 90.0)),
                Result(state=State.OK, summary="Temperature: 10 °C"),
                Result(
                    state=State.CRIT,
                    summary="Temperature trend: +10.0 °C per 5 min (warn/crit at +5 °C per 5 min/+10 °C per 5 min)",
                ),
                Result(
                    state=State.CRIT,
                    summary="Time until temperature limit reached: 40 minutes 0 seconds (warn/crit below 4 hours 0 minutes/2 hours 0 minutes)",
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
            ],
            id="rate value present",
        ),
        pytest.param(
            EnvironmentThresholdSensorModelFactory.build(
                name="thermal_sensor",
                sensor_type="thermal",
                value=0.0,
                value_units="C",
                threshold_state="normal",
                warning_high_threshold=20,
                warning_low_threshold=0,
                critical_high_threshold=90,
                critical_low_threshold=0,
            ),
            [
                Metric("temp", 0.0, levels=(20.0, 90.0)),
                Result(state=State.OK, summary="Temperature: 0 °C"),
                Result(state=State.OK, summary="Temperature trend: +0.0 °C per 5 min"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
            ],
            id="rate value 0",
        ),
    ],
)
def test_check_environment_threshold_thermal_trend(
    sensor_model: EnvironmentThresholdSensorModel,
    expected_result: CheckResult,
) -> None:
    section = {sensor_model.name: sensor_model}

    params = TempParamDict(
        input_unit="c",
        output_unit="c",
        trend_compute={
            "period": 5,
            "trend_levels": (5, 10),
            "trend_levels_lower": (5, 10),
            "trend_timeleft": (240, 120),
        },
    )

    value_store = {
        "temp.netapp_environment_thermal_thermal_sensor.dev.delta": (
            FIVE_MIN_AGO_SIMULATED,
            0.0,
        ),
        "temp.netapp_environment_thermal_thermal_sensor.delta": (
            FIVE_MIN_AGO_SIMULATED,
            0.0,
        ),
    }

    with time_machine.travel(NOW_SIMULATED, tick=False):
        result = list(
            check_environment_threshold(
                item="thermal_sensor", params=params, section=section, value_store=value_store
            )
        )

        assert result == expected_result

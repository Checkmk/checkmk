#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
from typing import Any, MutableMapping

import freezegun
import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    GetRateError,
    IgnoreResultsError,
    Metric,
    Result,
)
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.utils import temperature

UNIQUE_NAME = "unique_name"


def mock_value_store() -> MutableMapping[str, Any]:
    return {}


def test_check_trend_raises() -> None:
    with pytest.raises(IgnoreResultsError):
        _ = list(
            temperature._check_trend(
                {},  # uninitialized -> raise
                23.0,
                {"period": 2},
                "c",
                0.0,
                0.0,
                "my_test",
            )
        )


def test_check_trend_simple() -> None:
    with freezegun.freeze_time("1970-01-01 00:01:00"):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 17.0)},
                23.0,
                {"period": 2},
                "c",
                0.0,
                0.0,
                "my_test",
            )
        )
    assert results == [Result(state=state.OK, summary="Temperature trend: +12.0°C per 2 min")]


def test_check_trend_ok() -> None:
    with freezegun.freeze_time("1970-01-01 00:01:00"):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 17.0)},
                23.0,
                {
                    "period": 2,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-50.0, -55.5),
                },
                "c",
                0.0,
                0.0,
                "my_test",
            )
        )
    assert results == [Result(state=state.OK, summary="Temperature trend: +12.0°C per 2 min")]


def test_check_trend_warn_upper() -> None:
    with freezegun.freeze_time("1970-01-01 00:01:00"):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 17.0)},
                23.0,
                {
                    "period": 2,
                    "trend_levels": (10.0, 15.0),
                    "trend_levels_lower": (-10.0, -15.0),
                },
                "c",
                0.0,
                0.0,
                "my_test",
            )
        )
    assert results == [
        Result(
            state=state.WARN,
            summary="Temperature trend: +12.0°C per 2 min (warn/crit at +10.0°C per 2 min/+15.0°C per 2 min)",
        )
    ]


def test_check_trend_crit_upper() -> None:
    with freezegun.freeze_time("1970-01-01 00:01:00"):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 17.0)},
                23.0,
                {
                    "period": 2,
                    "trend_levels": (7.0, 10.0),
                    "trend_levels_lower": (-10.0, -15.0),
                },
                "c",
                0.0,
                0.0,
                "my_test",
            )
        )
    assert results == [
        Result(
            state=state.CRIT,
            summary="Temperature trend: +12.0°C per 2 min (warn/crit at +7.0°C per 2 min/+10.0°C per 2 min)",
        )
    ]


def test_check_trend_warn_lower() -> None:
    with freezegun.freeze_time("1970-01-01 00:01:00"):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, -17.0)},
                -23.0,
                {
                    "period": 2,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-10.0, -15.0),
                },
                "c",
                0.0,
                0.0,
                "my_test",
            )
        )
    assert results == [
        Result(
            state=state.WARN,
            summary="Temperature trend: -12.0°C per 2 min (warn/crit below -10.0°C per 2 min/-15.0°C per 2 min)",
        )
    ]


def test_check_trend_crit_lower() -> None:
    with freezegun.freeze_time("1970-01-01 00:01:00"):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, -17.0)},
                -23.0,
                {
                    "period": 2,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-5.0, -10.0),
                },
                "c",
                0.0,
                0.0,
                "my_test",
            )
        )
    assert results == [
        Result(
            state=state.CRIT,
            summary="Temperature trend: -12.0°C per 2 min (warn/crit below -5.0°C per 2 min/-10.0°C per 2 min)",
        )
    ]


def test_check_trend_time_period_ok() -> None:
    with freezegun.freeze_time("1970-01-01 00:01:00"):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 5.0)},
                10.0,
                {
                    "period": 1,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-50.0, -55.0),
                    "trend_timeleft": (5.0, 2.0),
                },
                "c",
                40.0,
                0.0,
                "my_test",
            )
        )
    assert results == [
        Result(state=state.OK, summary="Temperature trend: +5.0°C per 1 min"),
        Result(state=state.OK, summary="Time until temperature limit reached: 6 minutes 0 seconds"),
    ]


def test_check_trend_time_period_warn_upper() -> None:
    with freezegun.freeze_time("1970-01-01 00:01:00"):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 5.0)},
                10.0,
                {
                    "period": 1,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-50.0, -55.0),
                    "trend_timeleft": (7.0, 2.0),
                },
                "c",
                40.0,
                0.0,
                "my_test",
            )
        )
    assert results == [
        Result(state=state.OK, summary="Temperature trend: +5.0°C per 1 min"),
        Result(
            state=state.WARN,
            summary="Time until temperature limit reached: 6 minutes 0 seconds (warn/crit below 7 minutes 0 seconds/2 minutes 0 seconds)",
        ),
    ]


def test_check_trend_time_period_crit_upper() -> None:
    with freezegun.freeze_time("1970-01-01 00:01:00"):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 5.0)},
                10.0,
                {
                    "period": 1,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-50.0, -55.0),
                    "trend_timeleft": (8.0, 7.0),
                },
                "c",
                40.0,
                0.0,
                "my_test",
            )
        )
    assert results == [
        Result(state=state.OK, summary="Temperature trend: +5.0°C per 1 min"),
        Result(
            state=state.CRIT,
            summary="Time until temperature limit reached: 6 minutes 0 seconds (warn/crit below 8 minutes 0 seconds/7 minutes 0 seconds)",
        ),
    ]


def test_check_trend_time_period_warn_lower() -> None:
    with freezegun.freeze_time("1970-01-01 00:01:00"):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 10.0)},
                5.0,
                {
                    "period": 1,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-50.0, -55.0),
                    "trend_timeleft": (8.0, 6.0),
                },
                "c",
                40.0,
                -30.0,
                "my_test",
            )
        )
    assert results == [
        Result(state=state.OK, summary="Temperature trend: -5.0°C per 1 min"),
        Result(
            state=state.WARN,
            summary="Time until temperature limit reached: 7 minutes 0 seconds (warn/crit below 8 minutes 0 seconds/6 minutes 0 seconds)",
        ),
    ]


def test_check_trend_time_period_crit_lower() -> None:
    with freezegun.freeze_time("1970-01-01 00:01:00"):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 10.0)},
                5.0,
                {
                    "period": 1,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-50.0, -55.0),
                    "trend_timeleft": (8.0, 6.0),
                },
                "c",
                40.0,
                -10.0,
                "my_test",
            )
        )
    assert results == [
        Result(state=state.OK, summary="Temperature trend: -5.0°C per 1 min"),
        Result(
            state=state.CRIT,
            summary="Time until temperature limit reached: 3 minutes 0 seconds (warn/crit below 8 minutes 0 seconds/6 minutes 0 seconds)",
        ),
    ]


def test_check_trend_time_period_zero_lower_bound() -> None:
    with freezegun.freeze_time("1970-01-01 00:01:00"):
        results = list(
            temperature._check_trend(
                {"temp.my_test.delta": (0, 10.0)},
                5.0,
                {
                    "period": 1,
                    "trend_levels": (50.0, 55.0),
                    "trend_levels_lower": (-50.0, -55.0),
                    "trend_timeleft": (8.0, 6.0),
                },
                "c",
                40.0,
                0.0,
                "my_test",
            )
        )
    assert results == [
        Result(state=state.OK, summary="Temperature trend: -5.0°C per 1 min"),
        Result(
            state=state.CRIT,
            summary="Time until temperature limit reached: 1 minute 0 seconds (warn/crit below 8 minutes 0 seconds/6 minutes 0 seconds)",
        ),
    ]


def test_check_temperature_simple() -> None:
    results = list(
        temperature.check_temperature(
            23.0,
            None,
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
        )
    )
    assert results == [
        Metric(name="temp", value=23.0),
        Result(state=state.OK, summary="Temperature: 23.0°C"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (no levels found)",
        ),
    ]


def test_check_temperature_user_levels_ok() -> None:
    results = list(
        temperature.check_temperature(
            23.0,
            {
                "levels": (26.0, 30.0),
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
        )
    )
    assert results == [
        Metric("temp", 23.0, levels=(26.0, 30.0)),
        Result(state=state.OK, summary="Temperature: 23.0°C"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]


def test_check_temperature_user_levels_warn_upper() -> None:
    results = list(
        temperature.check_temperature(
            23.0,
            {
                "levels": (23.0, 30.0),
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
        )
    )
    assert results == [
        Metric("temp", 23.0, levels=(23.0, 30.0)),
        Result(state=state.WARN, summary="Temperature: 23.0°C (warn/crit at 23.0°C/30.0°C)"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]


def test_check_temperature_user_levels_crit_upper() -> None:
    results = list(
        temperature.check_temperature(
            30.0,
            {
                "levels": (23.0, 30.0),
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
        )
    )
    assert results == [
        Metric("temp", 30.0, levels=(23.0, 30.0)),
        Result(state=state.CRIT, summary="Temperature: 30.0°C (warn/crit at 23.0°C/30.0°C)"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]


def test_check_temperature_user_levels_warn_lower() -> None:
    results = list(
        temperature.check_temperature(
            -1.0,
            {
                "levels_lower": (0.0, -15.0),
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
        )
    )
    assert results == [
        Metric("temp", -1.0),
        Result(state=state.WARN, summary="Temperature: -1.0°C (warn/crit below 0.0°C/-15.0°C)"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]


def test_check_temperature_user_levels_crit_lower() -> None:
    results = list(
        temperature.check_temperature(
            -16.0,
            {
                "levels_lower": (0.0, -15.0),
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
        )
    )
    assert results == [
        Metric("temp", -16.0),
        Result(state=state.CRIT, summary="Temperature: -16.0°C (warn/crit below 0.0°C/-15.0°C)"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]


def test_check_temperature_output_unit() -> None:
    results = list(
        temperature.check_temperature(
            10.0,
            {
                "output_unit": "f",
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
        )
    )
    assert results == [
        Metric("temp", 10.0),
        Result(state=state.OK, summary="Temperature: 50.0°F"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (no levels found)",
        ),
    ]


def test_check_temperature_input_unit() -> None:
    results = list(
        temperature.check_temperature(
            50.0,
            {
                "input_unit": "f",
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
        )
    )
    assert results == [
        Metric("temp", 10.0),
        Result(state=state.OK, summary="Temperature: 10.0°C"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (no levels found)",
        ),
    ]


def test_check_temperature_device_levels_ok() -> None:
    results = list(
        temperature.check_temperature(
            10.0,
            None,
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
            dev_levels=(54.0, 70.0),
        )
    )
    assert results == [
        Metric("temp", 10.0, levels=(54.0, 70.0)),
        Result(state=state.OK, summary="Temperature: 10.0°C"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (used device levels)",
        ),
    ]


def test_check_temperature_device_levels_warn_upper() -> None:
    results = list(
        temperature.check_temperature(
            10.0,
            None,
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
            dev_levels=(10.0, 15.0),
        )
    )
    assert results == [
        Metric("temp", 10.0, levels=(10.0, 15.0)),
        Result(state=state.WARN, summary="Temperature: 10.0°C (warn/crit at 10.0°C/15.0°C)"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (used device levels)",
        ),
    ]


def test_check_temperature_device_levels_crit_upper() -> None:
    results = list(
        temperature.check_temperature(
            18.0,
            None,
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
            dev_levels=(10.0, 15.0),
        )
    )
    assert results == [
        Metric("temp", 18.0, levels=(10.0, 15.0)),
        Result(state=state.CRIT, summary="Temperature: 18.0°C (warn/crit at 10.0°C/15.0°C)"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (used device levels)",
        ),
    ]


def test_check_temperature_device_levels_warn_lower() -> None:
    results = list(
        temperature.check_temperature(
            0.0,
            None,
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
        )
    )
    assert results == [
        Metric("temp", 0.0, levels=(10.0, 15.0)),
        Result(state=state.WARN, summary="Temperature: 0.0°C (warn/crit below 1.0°C/-15.0°C)"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (used device levels)",
        ),
    ]


def test_check_temperature_device_levels_crit_lower() -> None:
    results = list(
        temperature.check_temperature(
            -20.0,
            None,
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
        )
    )
    assert results == [
        Metric("temp", -20.0, levels=(10.0, 15.0)),
        Result(state=state.CRIT, summary="Temperature: -20.0°C (warn/crit below 1.0°C/-15.0°C)"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (used device levels)",
        ),
    ]


def test_check_temperature_use_user_levels() -> None:
    results = list(
        temperature.check_temperature(
            -20.0,
            {
                "levels": (50.0, 75.0),
                "levels_lower": (-25.0, -30.0),
                "device_levels_handling": "usr",
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
        )
    )
    assert results == [
        Metric("temp", -20.0, levels=(50.0, 75.0)),
        Result(state=state.OK, summary="Temperature: -20.0°C"),
        Result(state=state.OK, notice="Configuration: only use user levels"),
    ]


def test_check_temperature_use_device_levels() -> None:
    results = list(
        temperature.check_temperature(
            -20.0,
            {
                "levels": (50.0, 75.0),
                "levels_lower": (-25.0, -30.0),
                "device_levels_handling": "dev",
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
        )
    )
    assert results == [
        Metric("temp", -20.0, levels=(10.0, 15.0)),
        Result(state=state.CRIT, summary="Temperature: -20.0°C (warn/crit below 1.0°C/-15.0°C)"),
        Result(state=state.OK, notice="Configuration: only use device levels"),
    ]


def test_check_temperature_default_device_levels() -> None:
    results = list(
        temperature.check_temperature(
            -20.0,
            {
                "levels": (50.0, 75.0),
                "levels_lower": (-25.0, -30.0),
                "device_levels_handling": "devdefault",
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
        )
    )
    assert results == [
        Metric("temp", -20.0, levels=(10.0, 15.0)),
        Result(state=state.CRIT, summary="Temperature: -20.0°C (warn/crit below 1.0°C/-15.0°C)"),
        Result(
            state=state.OK,
            notice="Configuration: prefer device levels over user levels (used device levels)",
        ),
    ]


def test_check_temperature_default_user_levels() -> None:
    results = list(
        temperature.check_temperature(
            -20.0,
            {
                "levels_lower": (-25.0, -30.0),
                "device_levels_handling": "usrdefault",
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
        )
    )
    assert results == [
        Metric("temp", -20.0),
        Result(state=state.OK, summary="Temperature: -20.0°C"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]


def test_check_temperature_use_device_default_no_levels() -> None:
    results = list(
        temperature.check_temperature(
            -20.0,
            {
                "device_levels_handling": "devdefault",
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
        )
    )
    assert results == [
        Metric("temp", -20.0),
        Result(state=state.OK, summary="Temperature: -20.0°C"),
        Result(
            state=state.OK,
            notice="Configuration: prefer device levels over user levels (no levels found)",
        ),
    ]


def test_check_temperature_use_user_default_device_levels() -> None:
    results = list(
        temperature.check_temperature(
            -20.0,
            {
                "device_levels_handling": "usrdefault",
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
            dev_levels_lower=(1.0, -15.0),
        )
    )
    assert results == [
        Metric("temp", -20.0),
        Result(state=state.CRIT, summary="Temperature: -20.0°C (warn/crit below 1.0°C/-15.0°C)"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (used device levels)",
        ),
    ]


def test_check_temperature_use_user_default_user_levels() -> None:
    results = list(
        temperature.check_temperature(
            -20.0,
            {
                "levels_lower": (-25.0, -30.0),
                "device_levels_handling": "usrdefault",
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
        )
    )
    assert results == [
        Metric("temp", -20.0),
        Result(state=state.OK, summary="Temperature: -20.0°C"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]


def test_check_temperature_use_user_default_no_levels() -> None:
    results = list(
        temperature.check_temperature(
            -20.0,
            {
                "device_levels_handling": "usrdefault",
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
        )
    )
    assert results == [
        Metric("temp", -20.0),
        Result(state=state.OK, summary="Temperature: -20.0°C"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (no levels found)",
        ),
    ]


def test_check_temperature_show_worst() -> None:
    results = list(
        temperature.check_temperature(
            -20.0,
            {
                "levels": (50.0, 75.0),
                "levels_lower": (-25.0, -30.0),
                "device_levels_handling": "worst",
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
        )
    )
    assert results == [
        Metric("temp", -20.0, levels=(10.0, 15.0)),
        Result(state=state.CRIT, summary="Temperature: -20.0°C (warn/crit below 1.0°C/-15.0°C)"),
        Result(state=state.OK, notice="Configuration: show most critical state"),
    ]


def test_check_temperature_show_best() -> None:
    results = list(
        temperature.check_temperature(
            -20.0,
            {
                "levels": (50.0, 75.0),
                "levels_lower": (-25.0, -30.0),
                "device_levels_handling": "best",
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
        )
    )
    assert results == [
        Metric("temp", -20.0, levels=(50.0, 75.0)),
        Result(state=state.OK, summary="Temperature: -20.0°C"),
        Result(state=state.OK, notice="Configuration: show least critical state"),
    ]


def test_check_temperature_device_status_override_best() -> None:
    results = list(
        temperature.check_temperature(
            -20.0,
            {
                "levels": (50.0, 75.0),
                "levels_lower": (0.0, -10.0),
                "device_levels_handling": "best",
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(-25.0, -30.0),
            dev_status=1,
            dev_status_name="banana",
        )
    )
    assert results == [
        Metric("temp", -20.0, levels=(10.0, 15.0)),
        Result(state=state.OK, summary="Temperature: -20.0°C"),
        Result(state=state.WARN, summary="State on device: banana"),
        Result(state=state.OK, notice="Configuration: show least critical state"),
    ]


def test_check_temperature_device_status_override_worst() -> None:
    results = list(
        temperature.check_temperature(
            5.0,
            {
                "levels": (50.0, 75.0),
                "levels_lower": (0.0, -10.0),
                "device_levels_handling": "worst",
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
            dev_levels=(10.0, 15.0),
            dev_levels_lower=(1.0, -15.0),
            dev_status=2,
            dev_status_name="banana",
        )
    )
    assert results == [
        Metric("temp", 5.0, levels=(10.0, 15.0)),
        Result(state=state.OK, summary="Temperature: 5.0°C"),
        Result(state=state.CRIT, summary="State on device: banana"),
        Result(state=state.OK, notice="Configuration: show most critical state"),
    ]


def test_check_temperature_device_status_override_ok() -> None:
    results = list(
        temperature.check_temperature(
            5.0,
            {
                "levels": (5.0, 10.0),
                "levels_lower": (0.0, -10.0),
                "device_levels_handling": "best",
            },
            unique_name=UNIQUE_NAME,
            value_store=mock_value_store(),
            dev_levels=(20.0, 25.0),
            dev_levels_lower=(1.0, -15.0),
            dev_status=0,
            dev_status_name="banana",
        )
    )
    assert results == [
        Metric("temp", 5.0, levels=(20.0, 25.0)),
        Result(state=state.OK, summary="Temperature: 5.0°C"),
        Result(state=state.OK, notice="State on device: banana"),
        Result(state=state.OK, notice="Configuration: show least critical state"),
    ]


def test_check_temperature_ignores_trend_computation() -> None:
    trend_params: temperature.TempParamDict = {"trend_compute": {"period": 30}}
    value_store = mock_value_store()

    # NOTE: We have to suppress the user AND device counter initializations. Although both
    # trends might be off during initialization we ignore this issue for now since the
    # temperatures between two check intervals should not deviate much and the trends should
    # be correct in the long run.
    with contextlib.suppress(GetRateError), freezegun.freeze_time("1970-01-01 00:00:00"):
        list(
            temperature.check_temperature(
                0.0,
                trend_params,
                unique_name=UNIQUE_NAME,
                value_store=value_store,
            )
        )
    with contextlib.suppress(GetRateError), freezegun.freeze_time("1970-01-01 00:15:00"):
        list(
            temperature.check_temperature(
                10.0,
                trend_params,
                unique_name=UNIQUE_NAME,
                value_store=value_store,
            )
        )
    with freezegun.freeze_time("1970-01-01 00:30:00"):
        results = list(
            temperature.check_temperature(
                20.0,
                trend_params,
                unique_name=UNIQUE_NAME,
                value_store=value_store,
            )
        )

    assert results == [
        Metric("temp", 20.0),
        Result(state=state.OK, summary="Temperature: 20.0°C"),
        Result(state=state.OK, summary="Temperature trend: +20.0°C per 30 min"),
        Result(
            state=state.OK,
            notice="Configuration: prefer user levels over device levels (no levels found)",
        ),
    ]

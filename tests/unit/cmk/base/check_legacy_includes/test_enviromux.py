#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.check_legacy_includes.enviromux import (
    check_enviromux_humidity,
    check_enviromux_temperature,
    check_enviromux_voltage,
    inventory_enviromux_humidity,
    inventory_enviromux_temperature,
    inventory_enviromux_voltage,
    parse_enviromux,
)

STRING_TABLE = [
    ["0", "1", "Internal Temperature", "292", "100", "500"],
    ["1", "2", "Internal Humidity", "17", "10", "75"],
    ["2", "3", "Input Voltage", "140", "120", "150"],
]


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [("Internal Temperature 0", {})],
            id="For every sensor that measures the temperature, a Service is created.",
        ),
        pytest.param(
            [],
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discover_enviromux_temperature(
    section: StringTable,
    expected_discovery_result: Sequence[tuple[str, Any]],
) -> None:
    assert (
        list(inventory_enviromux_temperature(parse_enviromux(section))) == expected_discovery_result
    )


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [("Internal Humidity 1", {})],
            id="For every sensor that measures the humidity, a Service is created.",
        ),
        pytest.param(
            [],
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discover_enviromux_humidity(
    section: StringTable,
    expected_discovery_result: Sequence[tuple[str, Any]],
) -> None:
    assert list(inventory_enviromux_humidity(parse_enviromux(section))) == expected_discovery_result


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [("Input Voltage 2", {})],
            id="For every sensor that measures the voltage, a Service is created.",
        ),
        pytest.param(
            [],
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discover_enviromux_voltage(
    section: StringTable,
    expected_discovery_result: Sequence[tuple[str, Any]],
) -> None:
    assert list(inventory_enviromux_voltage(parse_enviromux(section))) == expected_discovery_result


@pytest.mark.parametrize(
    "section, params, expected_check_result",
    [
        pytest.param(
            STRING_TABLE,
            {"levels": (35.0, 45.0)},
            [0, "29.2 °C", [("temp", 29.2, 35.0, 45.0)]],
            id="If the temperature of the sensor is below the upper WARN/CRIT levels and above the lower WARN/CRIT levels, the result is OK.",
        ),
        pytest.param(
            [
                ["0", "1", "Internal Temperature", "402", "400", "500"],
            ],
            {"levels": (35.0, 45.0)},
            [
                1,
                "40.2 °C (warn/crit at 35.0/45.0 °C) (device warn/crit below 40.0/40.0 °C)",
                [("temp", 40.2, 35.0, 45.0)],
            ],
            id="If the temperature of the sensor is above the WARN level, the result is WARN.",
        ),
        pytest.param(
            [
                ["0", "1", "Internal Temperature", "462", "400", "500"],
            ],
            {"levels": (35.0, 45.0)},
            [
                2,
                "46.2 °C (warn/crit at 35.0/45.0 °C) (device warn/crit below 40.0/40.0 °C)",
                [("temp", 46.2, 35.0, 45.0)],
            ],
            id="If the temperature of the sensor is above the CRIT level, the result is CRIT.",
        ),
        pytest.param(
            [
                ["0", "1", "Internal Temperature", "240", "400", "500"],
            ],
            {"levels_lower": (25.0, 20.0)},
            [
                1,
                "24.0 °C (warn/crit below 25.0/20.0 °C) (device warn/crit at 50.0/50.0 °C)",
                [("temp", 24.0, 50.0, 50.0)],
            ],
            id="If the temperature of the sensor is below the lower WARN level, the result is WARN.",
        ),
        pytest.param(
            [
                ["0", "1", "Internal Temperature", "190", "400", "500"],
            ],
            {"levels_lower": (25.0, 20.0)},
            [
                2,
                "19.0 °C (warn/crit below 25.0/20.0 °C) (device warn/crit at 50.0/50.0 °C)",
                [("temp", 19.0, 50.0, 50.0)],
            ],
            id="If the temperature of the sensor is below the lower CRIT level, the result is CRIT.",
        ),
    ],
)
def test_check_enviromux_temperature(
    section: StringTable,
    params: Mapping[str, tuple[float, float]],
    expected_check_result: Sequence[tuple[str, Any]],
) -> None:
    assert (
        list(
            check_enviromux_temperature(
                item="Internal Temperature 0",
                params=params,
                parsed=parse_enviromux(section),
            )
        )
        == expected_check_result
    )


@pytest.mark.parametrize(
    "section, params, expected_check_result",
    [
        pytest.param(
            STRING_TABLE,
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [0, "Input Voltage is 14.0 V", [("voltage", 14.0)]],
            id="If the voltage of the sensor is below the upper WARN/CRIT levels and above the lower WARN/CRIT levels, the result is OK.",
        ),
        pytest.param(
            [
                ["2", "3", "Input Voltage", "220", "120", "150"],
            ],
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [1, "Input Voltage is 22.0 V (warn/crit at 20.0/25.0)", [("voltage", 22.0)]],
            id="If the voltage of the sensor is above the WARN level, the result is WARN.",
        ),
        pytest.param(
            [
                ["2", "3", "Input Voltage", "260", "120", "150"],
            ],
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [2, "Input Voltage is 26.0 V (warn/crit at 20.0/25.0)", [("voltage", 26.0)]],
            id="If the voltage of the sensor is above the CRIT level, the result is CRIT.",
        ),
        pytest.param(
            [
                ["2", "3", "Input Voltage", "40", "120", "150"],
            ],
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [1, "Input Voltage is 4.0 V (warn/crit below 5.0/3.0)", [("voltage", 4.0)]],
            id="If the voltage of the sensor is below the lower WARN level, the result is WARN.",
        ),
        pytest.param(
            [
                ["2", "3", "Input Voltage", "20", "120", "150"],
            ],
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [2, "Input Voltage is 2.0 V (warn/crit below 5.0/3.0)", [("voltage", 2.0)]],
            id="If the voltage of the sensor is below the lower CRIT level, the result is CRIT.",
        ),
    ],
)
def test_check_enviromux_voltage(
    section: StringTable,
    params: Mapping[str, tuple[float, float]],
    expected_check_result: Sequence[tuple[str, Any]],
) -> None:
    assert (
        list(
            check_enviromux_voltage(
                item="Input Voltage 2",
                params=params,
                parsed=parse_enviromux(section),
            )
        )
        == expected_check_result
    )


@pytest.mark.parametrize(
    "section, params, expected_check_result",
    [
        pytest.param(
            STRING_TABLE,
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [0, "17.00%", [("humidity", 17, 20.0, 25.0, 0.0, 100.0)]],
            id="If the humidity of the sensor is below the upper WARN/CRIT levels and above the lower WARN/CRIT levels, the result is OK.",
        ),
        pytest.param(
            [
                ["1", "2", "Internal Humidity", "24", "10", "75"],
            ],
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [1, "24.00% (warn/crit at 20.00%/25.00%)", [("humidity", 24, 20.0, 25.0, 0.0, 100.0)]],
            id="If the humidity of the sensor is above the WARN level, the result is WARN.",
        ),
        pytest.param(
            [
                ["1", "2", "Internal Humidity", "27", "10", "75"],
            ],
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [2, "27.00% (warn/crit at 20.00%/25.00%)", [("humidity", 27, 20.0, 25.0, 0.0, 100.0)]],
            id="If the humidity of the sensor is above the CRIT level, the result is CRIT.",
        ),
        pytest.param(
            [
                ["1", "2", "Internal Humidity", "4", "10", "75"],
            ],
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [1, "4.00% (warn/crit below 5.00%/3.00%)", [("humidity", 4, 20.0, 25.0, 0.0, 100.0)]],
            id="If the humidity of the sensor is below the lower WARN level, the result is WARN.",
        ),
        pytest.param(
            [
                ["1", "2", "Internal Humidity", "2", "10", "75"],
            ],
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [2, "2.00% (warn/crit below 5.00%/3.00%)", [("humidity", 2, 20.0, 25.0, 0.0, 100.0)]],
            id="If the humidity of the sensor is below the lower CRIT level, the result is CRIT.",
        ),
    ],
)
def test_check_enviromux_humidity(
    section: StringTable,
    params: Mapping[str, tuple[float, float]],
    expected_check_result: Sequence[tuple[str, Any]],
) -> None:
    assert (
        list(
            check_enviromux_humidity(
                item="Internal Humidity 1",
                params=params,
                parsed=parse_enviromux(section),
            )
        )
        == expected_check_result
    )

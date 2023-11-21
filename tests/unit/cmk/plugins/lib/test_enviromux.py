#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.lib.enviromux import (
    check_enviromux_humidity,
    check_enviromux_temperature,
    check_enviromux_voltage,
    discover_enviromux_humidity,
    discover_enviromux_temperature,
    discover_enviromux_voltage,
    parse_enviromux,
)
from cmk.plugins.lib.temperature import TempParamType

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
            [Service(item="Internal Temperature 0")],
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
    expected_discovery_result: Sequence[Service],
) -> None:
    assert (
        list(discover_enviromux_temperature(parse_enviromux(section))) == expected_discovery_result
    )


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [Service(item="Internal Humidity 1")],
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
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discover_enviromux_humidity(parse_enviromux(section))) == expected_discovery_result


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [Service(item="Input Voltage 2")],
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
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discover_enviromux_voltage(parse_enviromux(section))) == expected_discovery_result


@pytest.mark.parametrize(
    "section, params, expected_check_result",
    [
        pytest.param(
            STRING_TABLE,
            {"levels": (35.0, 45.0)},
            [
                Metric("temp", 29.2, levels=(35.0, 45.0)),
                Result(state=State.OK, summary="Temperature: 29.2 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="If the temperature of the sensor is below the upper WARN/CRIT levels and above the lower WARN/CRIT levels, the result is OK.",
        ),
        pytest.param(
            [
                ["0", "1", "Internal Temperature", "402", "400", "500"],
            ],
            {"levels": (35.0, 45.0)},
            [
                Metric("temp", 40.2, levels=(35.0, 45.0)),
                Result(
                    state=State.WARN, summary="Temperature: 40.2 °C (warn/crit at 35.0 °C/45.0 °C)"
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="If the temperature of the sensor is above the WARN level, the result is WARN.",
        ),
        pytest.param(
            [
                ["0", "1", "Internal Temperature", "462", "400", "500"],
            ],
            {"levels": (35.0, 45.0)},
            [
                Metric("temp", 46.2, levels=(35.0, 45.0)),
                Result(
                    state=State.CRIT, summary="Temperature: 46.2 °C (warn/crit at 35.0 °C/45.0 °C)"
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="If the temperature of the sensor is above the CRIT level, the result is CRIT.",
        ),
        pytest.param(
            [
                ["0", "1", "Internal Temperature", "240", "400", "500"],
            ],
            {"levels_lower": (25.0, 20.0)},
            [
                Metric("temp", 24.0),
                Result(
                    state=State.WARN,
                    summary="Temperature: 24.0 °C (warn/crit below 25.0 °C/20.0 °C)",
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="If the temperature of the sensor is below the lower WARN level, the result is WARN.",
        ),
        pytest.param(
            [
                ["0", "1", "Internal Temperature", "190", "400", "500"],
            ],
            {"levels_lower": (25.0, 20.0)},
            [
                Metric("temp", 19.0),
                Result(
                    state=State.CRIT,
                    summary="Temperature: 19.0 °C (warn/crit below 25.0 °C/20.0 °C)",
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="If the temperature of the sensor is below the lower CRIT level, the result is CRIT.",
        ),
    ],
)
def test_check_enviromux_temperature(
    section: StringTable,
    params: TempParamType,
    expected_check_result: Sequence[Result | Metric],
) -> None:
    assert (
        list(
            check_enviromux_temperature(
                item="Internal Temperature 0",
                params=params,
                section=parse_enviromux(section),
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
            [
                Result(state=State.OK, summary="Input Voltage is V: 14.00"),
                Metric("voltage", 14.0, levels=(20.0, 25.0)),
            ],
            id="If the voltage of the sensor is below the upper WARN/CRIT levels and above the lower WARN/CRIT levels, the result is OK.",
        ),
        pytest.param(
            [
                ["2", "3", "Input Voltage", "220", "120", "150"],
            ],
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [
                Result(
                    state=State.WARN, summary="Input Voltage is V: 22.00 (warn/crit at 20.00/25.00)"
                ),
                Metric("voltage", 22.0, levels=(20.0, 25.0)),
            ],
            id="If the voltage of the sensor is above the WARN level, the result is WARN.",
        ),
        pytest.param(
            [
                ["2", "3", "Input Voltage", "260", "120", "150"],
            ],
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [
                Result(
                    state=State.CRIT, summary="Input Voltage is V: 26.00 (warn/crit at 20.00/25.00)"
                ),
                Metric("voltage", 26.0, levels=(20.0, 25.0)),
            ],
            id="If the voltage of the sensor is above the CRIT level, the result is CRIT.",
        ),
        pytest.param(
            [
                ["2", "3", "Input Voltage", "40", "120", "150"],
            ],
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [
                Result(
                    state=State.WARN, summary="Input Voltage is V: 4.00 (warn/crit below 5.00/3.00)"
                ),
                Metric("voltage", 4.0, levels=(20.0, 25.0)),
            ],
            id="If the voltage of the sensor is below the lower WARN level, the result is WARN.",
        ),
        pytest.param(
            [
                ["2", "3", "Input Voltage", "20", "120", "150"],
            ],
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [
                Result(
                    state=State.CRIT, summary="Input Voltage is V: 2.00 (warn/crit below 5.00/3.00)"
                ),
                Metric("voltage", 2.0, levels=(20.0, 25.0)),
            ],
            id="If the voltage of the sensor is below the lower CRIT level, the result is CRIT.",
        ),
    ],
)
def test_check_enviromux_voltage(
    section: StringTable,
    params: Mapping[str, tuple[float, float]],
    expected_check_result: Sequence[Result | Metric],
) -> None:
    assert (
        list(
            check_enviromux_voltage(
                item="Input Voltage 2",
                params=params,
                section=parse_enviromux(section),
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
            [
                Result(state=State.OK, summary="17.00%"),
                Metric("humidity", 17.0, levels=(20.0, 25.0), boundaries=(0.0, 100.0)),
            ],
            id="If the humidity of the sensor is below the upper WARN/CRIT levels and above the lower WARN/CRIT levels, the result is OK.",
        ),
        pytest.param(
            [
                ["1", "2", "Internal Humidity", "24", "10", "75"],
            ],
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [
                Result(state=State.WARN, summary="24.00% (warn/crit at 20.00%/25.00%)"),
                Metric("humidity", 24.0, levels=(20.0, 25.0), boundaries=(0.0, 100.0)),
            ],
            id="If the humidity of the sensor is above the WARN level, the result is WARN.",
        ),
        pytest.param(
            [
                ["1", "2", "Internal Humidity", "27", "10", "75"],
            ],
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [
                Result(state=State.CRIT, summary="27.00% (warn/crit at 20.00%/25.00%)"),
                Metric("humidity", 27.0, levels=(20.0, 25.0), boundaries=(0.0, 100.0)),
            ],
            id="If the humidity of the sensor is above the CRIT level, the result is CRIT.",
        ),
        pytest.param(
            [
                ["1", "2", "Internal Humidity", "4", "10", "75"],
            ],
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [
                Result(state=State.WARN, summary="4.00% (warn/crit below 5.00%/3.00%)"),
                Metric("humidity", 4.0, levels=(20.0, 25.0), boundaries=(0.0, 100.0)),
            ],
            id="If the humidity of the sensor is below the lower WARN level, the result is WARN.",
        ),
        pytest.param(
            [
                ["1", "2", "Internal Humidity", "2", "10", "75"],
            ],
            {"levels": (20.0, 25.0), "levels_lower": (5.0, 3.0)},
            [
                Result(state=State.CRIT, summary="2.00% (warn/crit below 5.00%/3.00%)"),
                Metric("humidity", 2.0, levels=(20.0, 25.0), boundaries=(0.0, 100.0)),
            ],
            id="If the humidity of the sensor is below the lower CRIT level, the result is CRIT.",
        ),
    ],
)
def test_check_enviromux_humidity(
    section: StringTable,
    params: Mapping[str, tuple[float, float]],
    expected_check_result: Sequence[Result | Metric],
) -> None:
    assert (
        list(
            check_enviromux_humidity(
                item="Internal Humidity 1",
                params=params,
                section=parse_enviromux(section),
            )
        )
        == expected_check_result
    )

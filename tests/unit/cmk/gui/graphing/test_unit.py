#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.config import Config
from cmk.gui.graphing._formatter import (
    AutoPrecision,
    DecimalFormatter,
    EngineeringScientificFormatter,
    IECFormatter,
    NotationFormatter,
    StrictPrecision,
    TimeFormatter,
)
from cmk.gui.graphing._unit import (
    _Conversion,
    ConvertibleUnitSpecification,
    DecimalNotation,
    EngineeringScientificNotation,
    IECNotation,
    NonConvertibleUnitSpecification,
    TimeNotation,
    user_specific_unit,
)
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.utils.temperate_unit import TemperatureUnit


@pytest.mark.parametrize(
    ["unit_specification", "expected_formatter"],
    [
        (
            ConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="X"),
                precision=AutoPrecision(digits=2),
            ),
            DecimalFormatter(
                symbol="X",
                precision=AutoPrecision(digits=2),
            ),
        ),
        (
            ConvertibleUnitSpecification(
                notation=IECNotation(symbol="Y"),
                precision=StrictPrecision(digits=0),
            ),
            IECFormatter(
                symbol="Y",
                precision=StrictPrecision(digits=0),
            ),
        ),
        (
            ConvertibleUnitSpecification(
                notation=TimeNotation(symbol="s"),
                precision=StrictPrecision(digits=3),
            ),
            TimeFormatter(
                symbol="s",
                precision=StrictPrecision(digits=3),
            ),
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_user_specific_unit(
    unit_specification: ConvertibleUnitSpecification,
    expected_formatter: NotationFormatter,
) -> None:
    unit = user_specific_unit(
        unit_specification,
        LoggedInUser(None),
        Config(),
        source_symbol_to_conversion_computer={},
    )
    assert unit.formatter == expected_formatter
    assert unit.conversion(1) == 1


@pytest.mark.usefixtures("request_context")
def test_user_specific_unit_convertible() -> None:
    def converter(v: float) -> float:
        return 2 * v

    unit = user_specific_unit(
        ConvertibleUnitSpecification(
            notation=DecimalNotation(symbol="X"),
            precision=AutoPrecision(digits=2),
        ),
        LoggedInUser(None),
        Config(),
        source_symbol_to_conversion_computer={
            "X": lambda *_: _Conversion(
                symbol="Y",
                converter=converter,
            )
        },
    )
    assert unit.formatter == DecimalFormatter(
        symbol="Y",
        precision=AutoPrecision(digits=2),
    )
    assert unit.conversion is converter


@pytest.mark.usefixtures("request_context")
def test_user_specific_unit_non_convertible() -> None:
    unit = user_specific_unit(
        NonConvertibleUnitSpecification(
            notation=EngineeringScientificNotation(symbol="X"),
            precision=AutoPrecision(digits=2),
        ),
        LoggedInUser(None),
        Config(),
        source_symbol_to_conversion_computer={
            "X": lambda *_: _Conversion(
                symbol="Y",
                converter=lambda v: 2 * v,
            )
        },
    )
    assert unit.formatter == EngineeringScientificFormatter(
        symbol="X",
        precision=AutoPrecision(digits=2),
    )
    assert unit.conversion(1) == 1


@pytest.mark.parametrize(
    [
        "user_temperature_unit",
        "default_temperature_unit",
        "source_symbol",
        "expected_symbol",
        "source_value",
        "expected_value",
    ],
    [
        pytest.param(
            None,
            TemperatureUnit.CELSIUS,
            "°C",
            "°C",
            1,
            1,
            id="celsius to celsius",
        ),
        pytest.param(
            TemperatureUnit.FAHRENHEIT,
            TemperatureUnit.CELSIUS,
            "°C",
            "°F",
            2,
            2 * 1.8 + 32,
            id="celsius to fahrenheit",
        ),
        pytest.param(
            TemperatureUnit.FAHRENHEIT,
            TemperatureUnit.CELSIUS,
            "°F",
            "°F",
            3,
            3,
            id="fahrenheit to fahrenheit",
        ),
        pytest.param(
            None,
            TemperatureUnit.CELSIUS,
            "°F",
            "°C",
            4,
            (4 - 32) / 1.8,
            id="fahrenheit to celsius",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_user_specific_unit_celsius_to_fahrenheit(
    user_temperature_unit: TemperatureUnit | None,
    default_temperature_unit: TemperatureUnit,
    source_symbol: str,
    expected_symbol: str,
    source_value: float,
    expected_value: float,
) -> None:
    user = LoggedInUser(None)
    if user_temperature_unit:
        user._set_attribute("temperature_unit", user_temperature_unit.value)
    config = Config(default_temperature_unit=default_temperature_unit.value)

    unit = user_specific_unit(
        ConvertibleUnitSpecification(
            notation=DecimalNotation(symbol=source_symbol),
            precision=AutoPrecision(digits=2),
        ),
        user,
        config,
    )
    assert unit.formatter.symbol == expected_symbol
    assert unit.conversion(source_value) == expected_value

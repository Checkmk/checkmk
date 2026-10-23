#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing_engine import (
    AutoPrecision,
    DecimalNotation,
    EngineeringScientificNotation,
    IECNotation,
    NonConvertibleUnit,
    SINotation,
    StandardScientificNotation,
    StrictPrecision,
    TimeNotation,
    Unit,
)
from cmk.gui.graphing import user_specific_unit
from cmk.gui.graphing._user_specific_unit import (
    user_unit_format,
)
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.shared_typing.cmk_time_series_graph import Precision as SharedPrecision
from cmk.shared_typing.cmk_time_series_graph import UnitFormat
from cmk.web.utils.unit_formatter import (
    DecimalFormatter,
    EngineeringScientificFormatter,
    IECFormatter,
    NotationFormatter,
    SIFormatter,
    StandardScientificFormatter,
    TimeFormatter,
)


@pytest.mark.parametrize(
    ["metric_unit", "expected_formatter"],
    [
        pytest.param(
            Unit(
                notation=DecimalNotation(symbol="U"),
                precision=AutoPrecision(digits=2),
            ),
            DecimalFormatter(
                symbol="U",
                precision_kind="auto",
                digits=2,
            ),
            id="decimal",
        ),
        pytest.param(
            Unit(
                notation=SINotation(symbol="U"),
                precision=StrictPrecision(digits=3),
            ),
            SIFormatter(
                symbol="U",
                precision_kind="strict",
                digits=3,
            ),
            id="si-strict-precision",
        ),
        pytest.param(
            Unit(
                notation=IECNotation(symbol="U"),
                precision=AutoPrecision(digits=2),
            ),
            IECFormatter(
                symbol="U",
                precision_kind="auto",
                digits=2,
            ),
            id="iec",
        ),
        pytest.param(
            Unit(
                notation=StandardScientificNotation(symbol="U"),
                precision=AutoPrecision(digits=2),
            ),
            StandardScientificFormatter(
                symbol="U",
                precision_kind="auto",
                digits=2,
            ),
            id="standard-scientific",
        ),
        pytest.param(
            Unit(
                notation=EngineeringScientificNotation(symbol="U"),
                precision=AutoPrecision(digits=2),
            ),
            EngineeringScientificFormatter(
                symbol="U",
                precision_kind="auto",
                digits=2,
            ),
            id="standard-scientific",
        ),
        pytest.param(
            Unit(
                notation=TimeNotation(symbol="s"),
                precision=AutoPrecision(digits=2),
            ),
            TimeFormatter(
                symbol="s",
                precision_kind="auto",
                digits=2,
            ),
            id="time",
        ),
    ],
)
def test_user_specific_unit_formatter(
    metric_unit: Unit,
    expected_formatter: NotationFormatter,
) -> None:
    unit = user_specific_unit(metric_unit, TemperatureUnit.CELSIUS)
    assert unit.formatter == expected_formatter
    assert unit.conversion(1) == 1


@pytest.mark.parametrize(
    ["metric_unit", "temperature_unit", "expected_formatter", "value", "expected_value"],
    [
        pytest.param(
            Unit(
                notation=DecimalNotation(symbol="°C"),
                precision=AutoPrecision(digits=2),
            ),
            TemperatureUnit.CELSIUS,
            DecimalFormatter(
                symbol="°C",
                precision_kind="auto",
                digits=2,
            ),
            10,
            10,
            id="celsius-celsius",
        ),
        pytest.param(
            Unit(
                notation=DecimalNotation(symbol="°C"),
                precision=AutoPrecision(digits=2),
            ),
            TemperatureUnit.FAHRENHEIT,
            DecimalFormatter(
                symbol="°F",
                precision_kind="auto",
                digits=2,
            ),
            10,
            50,
            id="celsius-fahrenheit",
        ),
        pytest.param(
            Unit(
                notation=DecimalNotation(symbol="°F"),
                precision=AutoPrecision(digits=2),
            ),
            TemperatureUnit.CELSIUS,
            DecimalFormatter(
                symbol="°C",
                precision_kind="auto",
                digits=2,
            ),
            50,
            10,
            id="fahrenheit-celsius",
        ),
        pytest.param(
            Unit(
                notation=DecimalNotation(symbol="°F"),
                precision=AutoPrecision(digits=2),
            ),
            TemperatureUnit.FAHRENHEIT,
            DecimalFormatter(
                symbol="°F",
                precision_kind="auto",
                digits=2,
            ),
            50,
            50,
            id="fahrenheit-fahrenheit",
        ),
    ],
)
def test_user_specific_unit_convertible(
    metric_unit: Unit,
    temperature_unit: TemperatureUnit,
    expected_formatter: NotationFormatter,
    value: float,
    expected_value: float,
) -> None:
    unit = user_specific_unit(metric_unit, temperature_unit)
    assert unit.formatter.symbol == expected_formatter.symbol
    assert unit.conversion(value) == expected_value


@pytest.mark.parametrize(
    ["metric_unit", "temperature_unit", "expected_formatter"],
    [
        pytest.param(
            NonConvertibleUnit(
                notation=DecimalNotation(symbol="°C"),
                precision=AutoPrecision(digits=2),
            ),
            TemperatureUnit.CELSIUS,
            DecimalFormatter(
                symbol="°C",
                precision_kind="auto",
                digits=2,
            ),
            id="celsius-celsius",
        ),
        pytest.param(
            NonConvertibleUnit(
                notation=DecimalNotation(symbol="°C"),
                precision=AutoPrecision(digits=2),
            ),
            TemperatureUnit.FAHRENHEIT,
            DecimalFormatter(
                symbol="°C",
                precision_kind="auto",
                digits=2,
            ),
            id="celsius-fahrenheit",
        ),
        pytest.param(
            NonConvertibleUnit(
                notation=DecimalNotation(symbol="°F"),
                precision=AutoPrecision(digits=2),
            ),
            TemperatureUnit.CELSIUS,
            DecimalFormatter(
                symbol="°F",
                precision_kind="auto",
                digits=2,
            ),
            id="fahrenheit-celsius",
        ),
        pytest.param(
            NonConvertibleUnit(
                notation=DecimalNotation(symbol="°F"),
                precision=AutoPrecision(digits=2),
            ),
            TemperatureUnit.FAHRENHEIT,
            DecimalFormatter(
                symbol="°F",
                precision_kind="auto",
                digits=2,
            ),
            id="fahrenheit-fahrenheit",
        ),
    ],
)
def test_user_specific_unit_not_convertible(
    metric_unit: NonConvertibleUnit,
    temperature_unit: TemperatureUnit,
    expected_formatter: NotationFormatter,
) -> None:
    unit = user_specific_unit(metric_unit, temperature_unit)
    assert unit.formatter.symbol == expected_formatter.symbol
    assert unit.conversion(123.456) == 123.456


def test_user_unit_format_converts_celsius_to_fahrenheit() -> None:
    unit_format, _conversion = user_unit_format(
        Unit(notation=DecimalNotation(symbol="°C"), precision=AutoPrecision(digits=2)),
        TemperatureUnit.FAHRENHEIT,
    )
    assert unit_format == UnitFormat(
        notation="decimal",
        symbol="°F",
        precision=SharedPrecision(type="auto", digits=2),
        convertible=False,
    )


def test_user_unit_format_leaves_a_non_temperature_unit_alone() -> None:
    unit_format, _conversion = user_unit_format(
        Unit(notation=SINotation(symbol="B"), precision=StrictPrecision(digits=3)),
        TemperatureUnit.FAHRENHEIT,
    )
    assert unit_format == UnitFormat(
        notation="si",
        symbol="B",
        precision=SharedPrecision(type="strict", digits=3),
        convertible=False,
    )

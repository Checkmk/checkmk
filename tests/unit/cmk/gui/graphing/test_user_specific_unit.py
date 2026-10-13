#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.graphing import (
    ConvertibleUnitSpecification,
    DecimalNotation,
    EngineeringScientificNotation,
    IECNotation,
    SINotation,
    StandardScientificNotation,
    TimeNotation,
    user_specific_unit,
    user_specific_unit_from_unit_format,
)
from cmk.gui.graphing._unit_specification import NonConvertibleUnitSpecification
from cmk.gui.graphing._user_specific_unit import (
    apply_temperature_unit,
    formatter_from_unit_format,
)
from cmk.gui.unit_formatter import (
    AutoPrecision,
    DecimalFormatter,
    EngineeringScientificFormatter,
    IECFormatter,
    NotationFormatter,
    SIFormatter,
    StandardScientificFormatter,
    StrictPrecision,
    TimeFormatter,
)
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.shared_typing.cmk_time_series_graph import Precision as SharedPrecision
from cmk.shared_typing.cmk_time_series_graph import UnitFormat


@pytest.mark.parametrize(
    ["unit_specification", "expected_formatter"],
    [
        pytest.param(
            ConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="U"),
                precision=AutoPrecision(digits=2),
            ),
            DecimalFormatter(
                symbol="U",
                precision=AutoPrecision(digits=2),
            ),
            id="decimal",
        ),
        pytest.param(
            ConvertibleUnitSpecification(
                notation=SINotation(symbol="U"),
                precision=AutoPrecision(digits=2),
            ),
            SIFormatter(
                symbol="U",
                precision=AutoPrecision(digits=2),
            ),
            id="si",
        ),
        pytest.param(
            ConvertibleUnitSpecification(
                notation=IECNotation(symbol="U"),
                precision=AutoPrecision(digits=2),
            ),
            IECFormatter(
                symbol="U",
                precision=AutoPrecision(digits=2),
            ),
            id="iec",
        ),
        pytest.param(
            ConvertibleUnitSpecification(
                notation=StandardScientificNotation(symbol="U"),
                precision=AutoPrecision(digits=2),
            ),
            StandardScientificFormatter(
                symbol="U",
                precision=AutoPrecision(digits=2),
            ),
            id="standard-scientific",
        ),
        pytest.param(
            ConvertibleUnitSpecification(
                notation=EngineeringScientificNotation(symbol="U"),
                precision=AutoPrecision(digits=2),
            ),
            EngineeringScientificFormatter(
                symbol="U",
                precision=AutoPrecision(digits=2),
            ),
            id="standard-scientific",
        ),
        pytest.param(
            ConvertibleUnitSpecification(
                notation=TimeNotation(symbol="s"),
                precision=AutoPrecision(digits=2),
            ),
            TimeFormatter(
                symbol="s",
                precision=AutoPrecision(digits=2),
            ),
            id="time",
        ),
    ],
)
def test_user_specific_unit_formatter(
    unit_specification: ConvertibleUnitSpecification,
    expected_formatter: NotationFormatter,
) -> None:
    unit = user_specific_unit(unit_specification, TemperatureUnit.CELSIUS)
    assert unit.formatter == expected_formatter
    assert unit.conversion(1) == 1


@pytest.mark.parametrize(
    ["unit_specification", "temperature_unit", "expected_formatter", "value", "expected_value"],
    [
        pytest.param(
            ConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="°C"),
                precision=AutoPrecision(digits=2),
            ),
            TemperatureUnit.CELSIUS,
            DecimalFormatter(
                symbol="°C",
                precision=AutoPrecision(digits=2),
            ),
            10,
            10,
            id="celsius-celsius",
        ),
        pytest.param(
            ConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="°C"),
                precision=AutoPrecision(digits=2),
            ),
            TemperatureUnit.FAHRENHEIT,
            DecimalFormatter(
                symbol="°F",
                precision=AutoPrecision(digits=2),
            ),
            10,
            50,
            id="celsius-fahrenheit",
        ),
        pytest.param(
            ConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="°F"),
                precision=AutoPrecision(digits=2),
            ),
            TemperatureUnit.CELSIUS,
            DecimalFormatter(
                symbol="°C",
                precision=AutoPrecision(digits=2),
            ),
            50,
            10,
            id="fahrenheit-celsius",
        ),
        pytest.param(
            ConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="°F"),
                precision=AutoPrecision(digits=2),
            ),
            TemperatureUnit.FAHRENHEIT,
            DecimalFormatter(
                symbol="°F",
                precision=AutoPrecision(digits=2),
            ),
            50,
            50,
            id="fahrenheit-fahrenheit",
        ),
    ],
)
def test_user_specific_unit_convertible(
    unit_specification: ConvertibleUnitSpecification,
    temperature_unit: TemperatureUnit,
    expected_formatter: NotationFormatter,
    value: float,
    expected_value: float,
) -> None:
    unit = user_specific_unit(unit_specification, temperature_unit)
    assert unit.formatter.symbol == expected_formatter.symbol
    assert unit.conversion(value) == expected_value


@pytest.mark.parametrize(
    ["unit_specification", "temperature_unit", "expected_formatter"],
    [
        pytest.param(
            NonConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="°C"),
                precision=AutoPrecision(digits=2),
            ),
            TemperatureUnit.CELSIUS,
            DecimalFormatter(
                symbol="°C",
                precision=AutoPrecision(digits=2),
            ),
            id="celsius-celsius",
        ),
        pytest.param(
            NonConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="°C"),
                precision=AutoPrecision(digits=2),
            ),
            TemperatureUnit.FAHRENHEIT,
            DecimalFormatter(
                symbol="°C",
                precision=AutoPrecision(digits=2),
            ),
            id="celsius-fahrenheit",
        ),
        pytest.param(
            NonConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="°F"),
                precision=AutoPrecision(digits=2),
            ),
            TemperatureUnit.CELSIUS,
            DecimalFormatter(
                symbol="°F",
                precision=AutoPrecision(digits=2),
            ),
            id="fahrenheit-celsius",
        ),
        pytest.param(
            NonConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="°F"),
                precision=AutoPrecision(digits=2),
            ),
            TemperatureUnit.FAHRENHEIT,
            DecimalFormatter(
                symbol="°F",
                precision=AutoPrecision(digits=2),
            ),
            id="fahrenheit-fahrenheit",
        ),
    ],
)
def test_user_specific_unit_not_convertible(
    unit_specification: NonConvertibleUnitSpecification,
    temperature_unit: TemperatureUnit,
    expected_formatter: NotationFormatter,
) -> None:
    unit = user_specific_unit(unit_specification, temperature_unit)
    assert unit.formatter.symbol == expected_formatter.symbol
    assert unit.conversion(123.456) == 123.456


@pytest.mark.parametrize(
    ["unit_format", "expected_formatter"],
    [
        pytest.param(
            UnitFormat(
                notation="decimal", symbol="U", precision=SharedPrecision(type="auto", digits=2)
            ),
            DecimalFormatter(symbol="U", precision=AutoPrecision(digits=2)),
            id="decimal",
        ),
        pytest.param(
            UnitFormat(
                notation="si", symbol="U", precision=SharedPrecision(type="strict", digits=3)
            ),
            SIFormatter(symbol="U", precision=StrictPrecision(digits=3)),
            id="si-strict-precision",
        ),
        pytest.param(
            UnitFormat(
                notation="iec", symbol="U", precision=SharedPrecision(type="auto", digits=2)
            ),
            IECFormatter(symbol="U", precision=AutoPrecision(digits=2)),
            id="iec",
        ),
        pytest.param(
            UnitFormat(
                notation="standard_scientific",
                symbol="U",
                precision=SharedPrecision(type="auto", digits=2),
            ),
            StandardScientificFormatter(symbol="U", precision=AutoPrecision(digits=2)),
            id="standard-scientific",
        ),
        pytest.param(
            UnitFormat(
                notation="engineering_scientific",
                symbol="U",
                precision=SharedPrecision(type="auto", digits=2),
            ),
            EngineeringScientificFormatter(symbol="U", precision=AutoPrecision(digits=2)),
            id="engineering-scientific",
        ),
        pytest.param(
            UnitFormat(
                notation="time", symbol="s", precision=SharedPrecision(type="auto", digits=2)
            ),
            TimeFormatter(symbol="s", precision=AutoPrecision(digits=2)),
            id="time",
        ),
    ],
)
def test_user_specific_unit_from_unit_format(
    unit_format: UnitFormat,
    expected_formatter: NotationFormatter,
) -> None:
    unit = user_specific_unit_from_unit_format(unit_format, TemperatureUnit.CELSIUS)
    assert unit.formatter == expected_formatter
    assert unit.conversion(1) == 1


def test_user_specific_unit_from_unit_format_converts_celsius_to_fahrenheit() -> None:
    unit_format = UnitFormat(
        notation="decimal", symbol="°C", precision=SharedPrecision(type="auto", digits=2)
    )
    unit = user_specific_unit_from_unit_format(unit_format, TemperatureUnit.FAHRENHEIT)
    assert unit.formatter.symbol == "°F"
    assert unit.conversion(10) == 50


def test_user_specific_unit_from_unit_format_not_convertible_keeps_a_literal_symbol() -> None:
    # A custom-graph user-defined unit sets convertible=False so a literal "°C" label is not
    # treated as a real temperature - see UnitFormat.convertible's own docstring.
    unit_format = UnitFormat(
        notation="decimal",
        symbol="°C",
        precision=SharedPrecision(type="auto", digits=2),
        convertible=False,
    )
    unit = user_specific_unit_from_unit_format(unit_format, TemperatureUnit.FAHRENHEIT)
    assert unit.formatter.symbol == "°C"
    assert unit.conversion(10) == 10


def test_apply_temperature_unit_celsius_to_fahrenheit() -> None:
    unit_format, conversion = apply_temperature_unit(
        UnitFormat(
            notation="decimal", symbol="°C", precision=SharedPrecision(type="auto", digits=2)
        ),
        TemperatureUnit.FAHRENHEIT,
    )
    assert unit_format == UnitFormat(
        notation="decimal",
        symbol="°F",
        precision=SharedPrecision(type="auto", digits=2),
        convertible=False,
    )
    assert conversion(20.0) == 68.0


def test_apply_temperature_unit_fahrenheit_to_celsius() -> None:
    unit_format, conversion = apply_temperature_unit(
        UnitFormat(
            notation="decimal", symbol="°F", precision=SharedPrecision(type="auto", digits=2)
        ),
        TemperatureUnit.CELSIUS,
    )
    assert unit_format.symbol == "°C"
    assert conversion(68.0) == 20.0


def test_apply_temperature_unit_celsius_to_celsius_is_the_identity() -> None:
    unit_format, conversion = apply_temperature_unit(
        UnitFormat(
            notation="decimal", symbol="°C", precision=SharedPrecision(type="auto", digits=2)
        ),
        TemperatureUnit.CELSIUS,
    )
    assert unit_format.symbol == "°C"
    assert conversion(20.0) == 20.0


def test_apply_temperature_unit_leaves_a_non_temperature_symbol_alone() -> None:
    unit_format, conversion = apply_temperature_unit(
        UnitFormat(notation="si", symbol="B", precision=SharedPrecision(type="strict", digits=3)),
        TemperatureUnit.FAHRENHEIT,
    )
    assert unit_format.symbol == "B"
    assert unit_format.precision == SharedPrecision(type="strict", digits=3)
    assert conversion(123.456) == 123.456


def test_apply_temperature_unit_respects_a_unit_that_opts_out() -> None:
    # A custom-graph unit whose label merely happens to read "°C" is not a temperature.
    unit_format, conversion = apply_temperature_unit(
        UnitFormat(
            notation="decimal",
            symbol="°C",
            precision=SharedPrecision(type="auto", digits=2),
            convertible=False,
        ),
        TemperatureUnit.FAHRENHEIT,
    )
    assert unit_format.symbol == "°C"
    assert conversion(20.0) == 20.0


def test_formatter_from_unit_format_keeps_a_temperature_symbol_as_given() -> None:
    formatter = formatter_from_unit_format(
        UnitFormat(
            notation="decimal", symbol="°C", precision=SharedPrecision(type="auto", digits=2)
        )
    )
    assert formatter == DecimalFormatter(symbol="°C", precision=AutoPrecision(digits=2))

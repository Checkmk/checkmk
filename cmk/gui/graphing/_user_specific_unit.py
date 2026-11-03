#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable
from dataclasses import dataclass

from cmk.graphing_engine import (
    NonConvertibleUnit,
    TemperatureUnit,
    Unit,
    unit_conversion,
)
from cmk.gui.logged_in import LoggedInUser
from cmk.shared_typing.cmk_time_series_graph import UnitFormat as SharedUnitFormat
from cmk.web.utils.unit_formatter import notation_formatter, NotationFormatter

from ._unit_format import unit_to_unit_format


@dataclass(frozen=True)
class UserSpecificUnit:
    formatter: NotationFormatter
    conversion: Callable[[float], float]


def user_unit_format(
    unit: Unit | NonConvertibleUnit, temperature_unit: TemperatureUnit
) -> tuple[SharedUnitFormat, Callable[[float], float]]:
    unit_format = unit_to_unit_format(unit)
    conversion = unit_conversion(unit, temperature_unit)
    return (
        SharedUnitFormat(
            notation=unit_format.notation,
            symbol=conversion.symbol,
            precision=unit_format.precision,
            convertible=False,
        ),
        conversion.converter,
    )


def user_specific_unit(
    unit: Unit | NonConvertibleUnit,
    temperature_unit: TemperatureUnit,
) -> UserSpecificUnit:
    unit_format, conversion = user_unit_format(unit, temperature_unit)
    return UserSpecificUnit(
        formatter=notation_formatter(
            unit_format.notation,
            unit_format.symbol,
            unit_format.precision.type,
            unit_format.precision.digits,
        ),
        conversion=conversion,
    )


def get_temperature_unit(user: LoggedInUser, temperature_unit: str) -> TemperatureUnit:
    return TemperatureUnit(user.get_attribute("temperature_unit") or temperature_unit)

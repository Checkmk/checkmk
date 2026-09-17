#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable
from dataclasses import replace
from typing import assert_never, Literal

from cmk.graphing_engine import (
    AutoPrecision,
    DecimalNotation,
    EngineeringScientificNotation,
    IECNotation,
    SINotation,
    StandardScientificNotation,
    StrictPrecision,
    TimeNotation,
    Unit,
)
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.shared_typing.cmk_time_series_graph import Precision, UnitFormat

from ._user_specific_unit import user_specific_unit_from_unit_format

type NotationName = Literal[
    "decimal", "si", "iec", "standard_scientific", "engineering_scientific", "time"
]
type PrecisionKind = Literal["auto", "strict"]


def notation_name(unit: Unit) -> NotationName:
    match unit.notation:
        case DecimalNotation():
            return "decimal"
        case SINotation():
            return "si"
        case IECNotation():
            return "iec"
        case StandardScientificNotation():
            return "standard_scientific"
        case EngineeringScientificNotation():
            return "engineering_scientific"
        case TimeNotation():
            return "time"
        case _:
            assert_never(unit.notation)


def precision_kind(unit: Unit) -> PrecisionKind:
    match unit.precision:
        case AutoPrecision():
            return "auto"
        case StrictPrecision():
            return "strict"
        case _:
            assert_never(unit.precision)


def unit_to_unit_format(unit: Unit) -> UnitFormat:
    return UnitFormat(
        notation=notation_name(unit),
        symbol=unit.notation.symbol,
        precision=Precision(type=precision_kind(unit), digits=unit.precision.digits),
    )


def unit_from_curves(units: Iterable[Unit]) -> UnitFormat | None:
    """The axis unit taken from the first of an ordered sequence of curve units.

    Every curve in a graph draws in one shared unit (enforced backend-side), so the axis unit is
    the unit of any curve; None when there are no units at all, in which case the renderer falls
    back to raw, unit-less ticks. Shared by _frontend.derive_y_axis_unit (the pre-evaluation
    Graph) and _graph_png._derived_y_axis_unit (the EvaluatedGraph), which carries the same
    CurveAttributes.unit on its curves but has no common curve type to walk with this one.
    """
    return next((unit_to_unit_format(unit) for unit in units), None)


def apply_temperature_unit(
    unit_format: UnitFormat, temperature_unit: TemperatureUnit
) -> tuple[UnitFormat, Callable[[float], float]]:
    """Unit and converter as a pair, so no caller relabels values without converting them.

    ``convertible=False`` tells the frontend the numbers are already converted."""
    user_specific = user_specific_unit_from_unit_format(unit_format, temperature_unit)
    return (
        replace(unit_format, symbol=user_specific.formatter.symbol, convertible=False),
        user_specific.conversion,
    )

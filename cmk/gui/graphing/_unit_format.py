#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import assert_never, Literal

from cmk.graphing_engine import (
    AutoPrecision,
    DecimalNotation,
    EngineeringScientificNotation,
    IECNotation,
    NonConvertibleUnit,
    Notation,
    Precision,
    SINotation,
    StandardScientificNotation,
    StrictPrecision,
    TimeNotation,
    Unit,
)
from cmk.shared_typing.cmk_time_series_graph import Precision as SharedPrecision
from cmk.shared_typing.cmk_time_series_graph import UnitFormat

type NotationName = Literal[
    "decimal", "si", "iec", "standard_scientific", "engineering_scientific", "time"
]
type PrecisionKind = Literal["auto", "strict"]


def notation_name(notation: Notation) -> NotationName:
    match notation:
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
            assert_never(notation)


def precision_kind(precision: Precision) -> PrecisionKind:
    match precision:
        case AutoPrecision():
            return "auto"
        case StrictPrecision():
            return "strict"
        case _:
            assert_never(precision)


def unit_to_unit_format(unit: Unit | NonConvertibleUnit) -> UnitFormat:
    return UnitFormat(
        notation=notation_name(unit.notation),
        symbol=unit.notation.symbol,
        precision=SharedPrecision(
            type=precision_kind(unit.precision), digits=unit.precision.digits
        ),
        convertible=None if isinstance(unit, Unit) else False,
    )

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
    SINotation,
    StandardScientificNotation,
    StrictPrecision,
    TimeNotation,
    Unit,
)
from cmk.shared_typing.cmk_time_series_graph import Precision, UnitFormat

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

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import assert_never, Literal


@dataclass(frozen=True)
class DecimalNotation:
    symbol: str


@dataclass(frozen=True)
class SINotation:
    symbol: str


@dataclass(frozen=True)
class IECNotation:
    symbol: str


@dataclass(frozen=True)
class StandardScientificNotation:
    symbol: str


@dataclass(frozen=True)
class EngineeringScientificNotation:
    symbol: str


@dataclass(frozen=True)
class TimeNotation:
    symbol: str = "s"


type Notation = (
    DecimalNotation
    | SINotation
    | IECNotation
    | StandardScientificNotation
    | EngineeringScientificNotation
    | TimeNotation
)


@dataclass(frozen=True)
class AutoPrecision:
    digits: int


@dataclass(frozen=True)
class StrictPrecision:
    digits: int


type Precision = AutoPrecision | StrictPrecision

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


@dataclass(frozen=True)
class Unit:
    notation: Notation
    precision: Precision


@dataclass(frozen=True)
class NonConvertibleUnit:
    notation: Notation
    precision: Precision


@dataclass(frozen=True, kw_only=True)
class CurveAttributes:
    title: str
    unit: Unit
    color: str

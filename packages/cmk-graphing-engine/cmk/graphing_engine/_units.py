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


def notation_from_name(name: str, symbol: str) -> Notation:
    match name:
        case "decimal":
            return DecimalNotation(symbol)
        case "si":
            return SINotation(symbol)
        case "iec":
            return IECNotation(symbol)
        case "standard_scientific":
            return StandardScientificNotation(symbol)
        case "engineering_scientific":
            return EngineeringScientificNotation(symbol)
        case "time":
            return TimeNotation(symbol)
        case other:
            raise ValueError(f"unknown notation: {other!r}")


def precision_kind(precision: Precision) -> PrecisionKind:
    match precision:
        case AutoPrecision():
            return "auto"
        case StrictPrecision():
            return "strict"
        case _:
            assert_never(precision)


def precision_from_kind(kind: str, digits: int) -> Precision:
    match kind:
        case "auto":
            return AutoPrecision(digits)
        case "strict":
            return StrictPrecision(digits)
        case other:
            raise ValueError(f"unknown precision: {other!r}")


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

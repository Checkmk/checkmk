#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.graphing_engine import (
    NonConvertibleUnit,
    Notation,
    notation_from_name,
    notation_name,
    Precision,
    precision_from_kind,
    precision_kind,
    Unit,
)

from ._decoding import ensure_type


def unit_to_specification(unit: Unit | NonConvertibleUnit) -> Mapping[str, object]:
    return {
        "type": "convertible" if isinstance(unit, Unit) else "non_convertible",
        "notation": {"type": notation_name(unit.notation), "symbol": unit.notation.symbol},
        "precision": {"type": precision_kind(unit.precision), "digits": unit.precision.digits},
    }


def _notation_from_specification(raw: object) -> Notation:
    specification = ensure_type(raw, dict)
    return notation_from_name(
        ensure_type(specification["type"], str), ensure_type(specification["symbol"], str)
    )


def _precision_from_specification(raw: object) -> Precision:
    specification = ensure_type(raw, dict)
    return precision_from_kind(
        ensure_type(specification["type"], str), ensure_type(specification["digits"], int)
    )


def _unit_from_specification(raw: object) -> Unit | NonConvertibleUnit:
    specification = ensure_type(raw, dict)
    notation = _notation_from_specification(specification["notation"])
    precision = _precision_from_specification(specification["precision"])
    match specification["type"]:
        case "convertible":
            return Unit(notation=notation, precision=precision)
        case "non_convertible":
            return NonConvertibleUnit(notation=notation, precision=precision)
        case other:
            raise ValueError(f"unknown unit: {other!r}")


def unit_from_specification(raw: object) -> Unit | NonConvertibleUnit:
    try:
        return _unit_from_specification(raw)
    except (KeyError, TypeError) as e:
        raise ValueError(f"malformed unit: {raw!r}") from e

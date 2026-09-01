#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from cmk.gui.graphing._engine_unit_format import unit_to_unit_format
from cmk.shared_typing.cmk_time_series_graph import Precision, UnitFormat


def test_unit_to_unit_format_decimal_auto_precision() -> None:
    unit = Unit(notation=DecimalNotation("%"), precision=AutoPrecision(2))
    assert unit_to_unit_format(unit) == UnitFormat(
        notation="decimal", symbol="%", precision=Precision(type="auto", digits=2)
    )


def test_unit_to_unit_format_si_strict_precision() -> None:
    unit = Unit(notation=SINotation("B/s"), precision=StrictPrecision(3))
    assert unit_to_unit_format(unit) == UnitFormat(
        notation="si", symbol="B/s", precision=Precision(type="strict", digits=3)
    )


def test_unit_to_unit_format_covers_every_notation() -> None:
    for notation, expected in (
        (IECNotation("B"), "iec"),
        (StandardScientificNotation(""), "standard_scientific"),
        (EngineeringScientificNotation(""), "engineering_scientific"),
        (TimeNotation(), "time"),
    ):
        unit = Unit(notation=notation, precision=AutoPrecision(2))
        assert unit_to_unit_format(unit).notation == expected

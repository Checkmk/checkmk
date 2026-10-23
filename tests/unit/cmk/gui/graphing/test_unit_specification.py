#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
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
from cmk.gui.graphing import unit_from_specification, unit_to_specification


def test_a_unit_is_stored_as_a_convertible_specification() -> None:
    assert unit_to_specification(Unit(notation=IECNotation("B"), precision=AutoPrecision(2))) == {
        "type": "convertible",
        "notation": {"type": "iec", "symbol": "B"},
        "precision": {"type": "auto", "digits": 2},
    }


def test_a_non_convertible_unit_is_stored_as_such() -> None:
    assert unit_to_specification(
        NonConvertibleUnit(notation=DecimalNotation("°C"), precision=StrictPrecision(1))
    ) == {
        "type": "non_convertible",
        "notation": {"type": "decimal", "symbol": "°C"},
        "precision": {"type": "strict", "digits": 1},
    }


@pytest.mark.parametrize(
    "unit",
    [
        Unit(notation=DecimalNotation(""), precision=AutoPrecision(2)),
        Unit(notation=SINotation("Hz"), precision=StrictPrecision(3)),
        Unit(notation=IECNotation("B/s"), precision=AutoPrecision(1)),
        Unit(notation=StandardScientificNotation("m"), precision=AutoPrecision(4)),
        Unit(notation=EngineeringScientificNotation("A"), precision=StrictPrecision(0)),
        Unit(notation=TimeNotation(), precision=AutoPrecision(2)),
        NonConvertibleUnit(notation=DecimalNotation("°F"), precision=AutoPrecision(2)),
    ],
)
def test_a_stored_unit_reads_back_as_what_it_was(unit: Unit | NonConvertibleUnit) -> None:
    assert unit_from_specification(unit_to_specification(unit)) == unit


@pytest.mark.parametrize(
    "specification",
    [
        pytest.param(
            {
                "type": "convertible",
                "notation": {"type": "roman", "symbol": ""},
                "precision": {"type": "auto", "digits": 2},
            },
            id="unknown notation",
        ),
        pytest.param(
            {
                "type": "convertible",
                "notation": {"type": "decimal", "symbol": ""},
                "precision": {"type": "rough", "digits": 2},
            },
            id="unknown precision",
        ),
        pytest.param(
            {
                "type": "translatable",
                "notation": {"type": "decimal", "symbol": ""},
                "precision": {"type": "auto", "digits": 2},
            },
            id="unknown unit kind",
        ),
        pytest.param("decimal", id="unit not a mapping"),
        pytest.param(
            {
                "type": "convertible",
                "notation": {"type": "decimal"},
                "precision": {"type": "auto", "digits": 2},
            },
            id="symbol missing",
        ),
        pytest.param(
            {
                "type": "convertible",
                "notation": {"type": "decimal", "symbol": ""},
                "precision": {"type": "auto", "digits": "2"},
            },
            id="digits not a number",
        ),
    ],
)
def test_an_unknown_or_malformed_stored_unit_is_refused(specification: object) -> None:
    with pytest.raises(ValueError):
        unit_from_specification(specification)

#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal

import pytest

from cmk.gui.graphing._parser import (
    DecimalFormatter,
    EngineeringScientificFormatter,
    IECFormatter,
    Label,
    parse_or_add_unit,
    SIFormatter,
    StandardScientificFormatter,
    TimeFormatter,
)

from cmk.graphing.v1 import metrics


@pytest.mark.parametrize(
    "precision, value, expected",
    [
        pytest.param(
            metrics.AutoPrecision(0),
            0,
            "0 unit",
            id="zero",
        ),
        pytest.param(
            metrics.AutoPrecision(0),
            1,
            "1 unit",
            id="one",
        ),
        #
        pytest.param(
            metrics.AutoPrecision(0),
            0.006789,
            "0.007 unit",
            id="small-zeros-auto-0",
        ),
        pytest.param(
            metrics.StrictPrecision(0),
            0.006789,
            "0 unit",
            id="small-zeros-strict-0",
        ),
        pytest.param(
            metrics.AutoPrecision(1),
            0.006789,
            "0.007 unit",
            id="small-zeros-auto-1",
        ),
        pytest.param(
            metrics.StrictPrecision(1),
            0.006789,
            "0 unit",
            id="small-zeros-strict-1",
        ),
        pytest.param(
            metrics.AutoPrecision(0),
            0.6789,
            "1 unit",
            id="small-no-zeros-auto-0",
        ),
        pytest.param(
            metrics.StrictPrecision(0),
            0.6789,
            "1 unit",
            id="small-no-zeros-strict-0",
        ),
        pytest.param(
            metrics.AutoPrecision(1),
            0.6789,
            "0.7 unit",
            id="small-no-zeros-auto-1",
        ),
        pytest.param(
            metrics.StrictPrecision(1),
            0.6789,
            "0.7 unit",
            id="small-no-zeros-strict-1",
        ),
        #
        pytest.param(
            metrics.AutoPrecision(0),
            12345.006789,
            "12345.007 unit",
            id="large-zeros-auto-0",
        ),
        pytest.param(
            metrics.StrictPrecision(0),
            12345.006789,
            "12345 unit",
            id="large-zeros-strict-0",
        ),
        pytest.param(
            metrics.AutoPrecision(1),
            12345.006789,
            "12345.007 unit",
            id="large-zeros-auto-1",
        ),
        pytest.param(
            metrics.StrictPrecision(1),
            12345.006789,
            "12345 unit",
            id="large-zeros-strict-1",
        ),
        pytest.param(
            metrics.AutoPrecision(0),
            12345.6789,
            "12346 unit",
            id="large-no-zeros-auto-0",
        ),
        pytest.param(
            metrics.StrictPrecision(0),
            12345.6789,
            "12346 unit",
            id="large-no-zeros-strict-0",
        ),
        pytest.param(
            metrics.AutoPrecision(1),
            12345.6789,
            "12345.7 unit",
            id="large-no-zeros-auto-1",
        ),
        pytest.param(
            metrics.StrictPrecision(1),
            12345.6789,
            "12345.7 unit",
            id="large-no-zeros-strict-1",
        ),
    ],
)
def test_parse_or_add_unit(
    precision: metrics.AutoPrecision | metrics.StrictPrecision, value: int | float, expected: str
) -> None:
    unit = metrics.Unit(metrics.DecimalNotation("unit"), precision)
    assert parse_or_add_unit(unit)["render"](value) == expected


@pytest.mark.parametrize(
    "notation, value, expected",
    [
        pytest.param(
            metrics.SINotation("unit"),
            0.0000123456789,
            "12.35 μunit",
            id="si-small",
        ),
        pytest.param(
            metrics.SINotation("unit"),
            123456.789,
            "123.46 kunit",
            id="si-large",
        ),
        pytest.param(
            metrics.SINotation("unit"),
            999.999,
            "1000 unit",
            id="si-large-border",
        ),
        pytest.param(
            metrics.IECNotation("unit"),
            0.0000123456789,
            "0 unit",
            id="iec-small",
        ),
        pytest.param(
            metrics.IECNotation("unit"),
            123456.789,
            "120.56 Kiunit",
            id="iec-large",
        ),
        pytest.param(
            metrics.IECNotation("unit"),
            1023.999,
            "1024 unit",
            id="iec-large-border",
        ),
        pytest.param(
            metrics.StandardScientificNotation("unit"),
            0.0000123456789,
            "1.23e-5 unit",
            id="standard-scientific-small",
        ),
        pytest.param(
            metrics.StandardScientificNotation("unit"),
            123456.789,
            "1.23e+5 unit",
            id="standard-scientific-large",
        ),
        pytest.param(
            metrics.StandardScientificNotation("unit"),
            0.00001,
            "1e-5 unit",
            id="standard-scientific-small-power-of-ten",
        ),
        pytest.param(
            metrics.StandardScientificNotation("unit"),
            100000.0,
            "1e+5 unit",
            id="standard-scientific-large-power-of-ten",
        ),
        pytest.param(
            metrics.EngineeringScientificNotation("unit"),
            0.0000123456789,
            "12.35e-6 unit",
            id="engineering-scientific-small",
        ),
        pytest.param(
            metrics.EngineeringScientificNotation("unit"),
            123456.789,
            "123.46e+3 unit",
            id="engineering-scientific-large",
        ),
        pytest.param(
            metrics.EngineeringScientificNotation("unit"),
            0.00001,
            "10e-6 unit",
            id="engineering-scientific-small-power-of-ten",
        ),
        pytest.param(
            metrics.EngineeringScientificNotation("unit"),
            1000000.0,
            "1e+6 unit",
            id="engineering-scientific-large-power-of-ten",
        ),
        pytest.param(
            metrics.EngineeringScientificNotation("unit"),
            100000.0,
            "100e+3 unit",
            id="engineering-scientific-large-power-of-ten-2",
        ),
        pytest.param(
            metrics.EngineeringScientificNotation("unit"),
            120000.0,
            "120e+3 unit",
            id="engineering-scientific-large-power-of-ten-2",
        ),
        pytest.param(
            metrics.TimeNotation(),
            0.0000123456789,
            "12.35 μs",
            id="time-small",
        ),
        pytest.param(
            metrics.TimeNotation(),
            137,
            "2 min 17 s",
            id="time-minutes",
        ),
        pytest.param(
            metrics.TimeNotation(),
            4312,
            "1 h 12 min",
            id="time-hours",
        ),
        pytest.param(
            metrics.TimeNotation(),
            123456.789,
            "1 d 10 h",
            id="time-large",
        ),
        pytest.param(
            metrics.TimeNotation(),
            86399.999,
            "24 h",
            id="time-large-border",
        ),
    ],
)
def test_render_unit_notation(
    notation: (
        metrics.SINotation
        | metrics.IECNotation
        | metrics.StandardScientificNotation
        | metrics.EngineeringScientificNotation
        | metrics.TimeNotation
    ),
    value: int | float,
    expected: str,
) -> None:
    unit = metrics.Unit(notation, metrics.StrictPrecision(2))
    assert parse_or_add_unit(unit)["render"](value) == expected


@pytest.mark.parametrize(
    "unit, expected",
    [
        #
        pytest.param(
            metrics.Unit(metrics.DecimalNotation("unit"), metrics.AutoPrecision(2)),
            """v => new cmk.number_format.DecimalFormatter(
    "unit",
    new cmk.number_format.AutoPrecision(2),
).render(v)""",
            id="decimal-auto",
        ),
        pytest.param(
            metrics.Unit(metrics.DecimalNotation("unit"), metrics.StrictPrecision(2)),
            """v => new cmk.number_format.DecimalFormatter(
    "unit",
    new cmk.number_format.StrictPrecision(2),
).render(v)""",
            id="decimal-strict",
        ),
        #
        pytest.param(
            metrics.Unit(metrics.SINotation("unit"), metrics.AutoPrecision(2)),
            """v => new cmk.number_format.SIFormatter(
    "unit",
    new cmk.number_format.AutoPrecision(2),
).render(v)""",
            id="si-auto",
        ),
        pytest.param(
            metrics.Unit(metrics.SINotation("unit"), metrics.StrictPrecision(2)),
            """v => new cmk.number_format.SIFormatter(
    "unit",
    new cmk.number_format.StrictPrecision(2),
).render(v)""",
            id="si-strict",
        ),
        #
        pytest.param(
            metrics.Unit(metrics.IECNotation("unit"), metrics.AutoPrecision(2)),
            """v => new cmk.number_format.IECFormatter(
    "unit",
    new cmk.number_format.AutoPrecision(2),
).render(v)""",
            id="iec-auto",
        ),
        pytest.param(
            metrics.Unit(metrics.IECNotation("unit"), metrics.StrictPrecision(2)),
            """v => new cmk.number_format.IECFormatter(
    "unit",
    new cmk.number_format.StrictPrecision(2),
).render(v)""",
            id="iec-strict",
        ),
        #
        pytest.param(
            metrics.Unit(metrics.StandardScientificNotation("unit"), metrics.AutoPrecision(2)),
            """v => new cmk.number_format.StandardScientificFormatter(
    "unit",
    new cmk.number_format.AutoPrecision(2),
).render(v)""",
            id="standard-scientific-auto",
        ),
        pytest.param(
            metrics.Unit(metrics.StandardScientificNotation("unit"), metrics.StrictPrecision(2)),
            """v => new cmk.number_format.StandardScientificFormatter(
    "unit",
    new cmk.number_format.StrictPrecision(2),
).render(v)""",
            id="standard-scientific-strict",
        ),
        #
        pytest.param(
            metrics.Unit(metrics.EngineeringScientificNotation("unit"), metrics.AutoPrecision(2)),
            """v => new cmk.number_format.EngineeringScientificFormatter(
    "unit",
    new cmk.number_format.AutoPrecision(2),
).render(v)""",
            id="engineering-scientific-auto",
        ),
        pytest.param(
            metrics.Unit(metrics.EngineeringScientificNotation("unit"), metrics.StrictPrecision(2)),
            """v => new cmk.number_format.EngineeringScientificFormatter(
    "unit",
    new cmk.number_format.StrictPrecision(2),
).render(v)""",
            id="engineering-scientific-strict",
        ),
        #
        pytest.param(
            metrics.Unit(metrics.TimeNotation(), metrics.AutoPrecision(2)),
            """v => new cmk.number_format.TimeFormatter(
    "s",
    new cmk.number_format.AutoPrecision(2),
).render(v)""",
            id="time-auto",
        ),
        pytest.param(
            metrics.Unit(metrics.TimeNotation(), metrics.StrictPrecision(2)),
            """v => new cmk.number_format.TimeFormatter(
    "s",
    new cmk.number_format.StrictPrecision(2),
).render(v)""",
            id="time-strict",
        ),
    ],
)
def test_js_render_unit_notation(unit: metrics.Unit, expected: str) -> None:
    assert parse_or_add_unit(unit)["js_render"] == expected


@pytest.mark.parametrize(
    "formatter, max_y, expected_ident, expected_labels",
    [
        pytest.param(
            DecimalFormatter("u", metrics.AutoPrecision(2)),
            0.00123,
            "Decimal",
            [
                Label(0.0002, "0.0002 u"),
                Label(0.0004, "0.0004 u"),
                Label(0.0006000000000000001, "0.0006 u"),
                Label(0.0008, "0.0008 u"),
                Label(0.001, "0.001 u"),
                Label(0.0012000000000000001, "0.0012 u"),
            ],
            id="decimal-small",
        ),
        pytest.param(
            DecimalFormatter("u", metrics.AutoPrecision(2)),
            123456.789,
            "Decimal",
            [
                Label(20000, "20000 u"),
                Label(40000, "40000 u"),
                Label(60000, "60000 u"),
                Label(80000, "80000 u"),
                Label(100000, "100000 u"),
                Label(120000, "120000 u"),
            ],
            id="decimal-large",
        ),
        pytest.param(
            SIFormatter("u", metrics.AutoPrecision(2)),
            0.00123,
            "SI",
            [
                Label(0.0002, "0.2 mu"),
                Label(0.0004, "0.4 mu"),
                Label(0.0006000000000000001, "0.6 mu"),
                Label(0.0008, "0.8 mu"),
                Label(0.001, "1 mu"),
                Label(0.0012000000000000001, "1.2 mu"),
            ],
            id="si-small",
        ),
        pytest.param(
            SIFormatter("u", metrics.AutoPrecision(2)),
            123456.789,
            "SI",
            [
                Label(20000, "20 ku"),
                Label(40000, "40 ku"),
                Label(60000, "60 ku"),
                Label(80000, "80 ku"),
                Label(100000, "100 ku"),
                Label(120000, "120 ku"),
            ],
            id="si-large",
        ),
        pytest.param(
            IECFormatter("u", metrics.AutoPrecision(2)),
            0.00123,
            "IEC",
            [
                Label(0.0002, "0.0002 u"),
                Label(0.0004, "0.0004 u"),
                Label(0.0006000000000000001, "0.0006 u"),
                Label(0.0008, "0.0008 u"),
                Label(0.001, "0.001 u"),
                Label(0.0012000000000000001, "0.0012 u"),
            ],
            id="iec-small",
        ),
        pytest.param(
            IECFormatter("u", metrics.AutoPrecision(2)),
            123456.789,
            "IEC",
            [
                Label(16384, "16 Kiu"),
                Label(32768, "32 Kiu"),
                Label(49152, "48 Kiu"),
                Label(65536, "64 Kiu"),
                Label(81920, "80 Kiu"),
                Label(98304, "96 Kiu"),
                Label(114688, "112 Kiu"),
            ],
            id="iec-large",
        ),
        pytest.param(
            StandardScientificFormatter("u", metrics.AutoPrecision(2)),
            0.00123,
            "StandardScientific",
            [
                Label(0.0002, "2e-4 u"),
                Label(0.0004, "4e-4 u"),
                Label(0.0006000000000000001, "6e-4 u"),
                Label(0.0008, "8e-4 u"),
                Label(0.001, "1e-3 u"),
                Label(0.0012000000000000001, "1.2e-3 u"),
            ],
            id="std-sci-small",
        ),
        pytest.param(
            StandardScientificFormatter("u", metrics.AutoPrecision(2)),
            123456.789,
            "StandardScientific",
            [
                Label(20000, "2e+4 u"),
                Label(40000, "4e+4 u"),
                Label(60000, "6e+4 u"),
                Label(80000, "8e+4 u"),
                Label(100000, "1e+5 u"),
                Label(120000, "1.2e+5 u"),
            ],
            id="std-sci-large",
        ),
        pytest.param(
            EngineeringScientificFormatter("u", metrics.AutoPrecision(2)),
            0.00123,
            "EngineeringScientific",
            [
                Label(0.0002, "200e-6 u"),
                Label(0.0004, "400e-6 u"),
                Label(0.0006000000000000001, "600e-6 u"),
                Label(0.0008, "800e-6 u"),
                Label(0.001, "1e-3 u"),
                Label(0.0012000000000000001, "1.2e-3 u"),
            ],
            id="eng-sci-small",
        ),
        pytest.param(
            EngineeringScientificFormatter("u", metrics.AutoPrecision(2)),
            123456.789,
            "EngineeringScientific",
            [
                Label(20000, "20e+3 u"),
                Label(40000, "40e+3 u"),
                Label(60000, "60e+3 u"),
                Label(80000, "80e+3 u"),
                Label(100000, "100e+3 u"),
                Label(120000, "120e+3 u"),
            ],
            id="eng-sci-large",
        ),
        pytest.param(
            TimeFormatter("s", metrics.AutoPrecision(2)),
            0.00123,
            "Time",
            [
                Label(0.0002, "0.2 ms"),
                Label(0.0004, "0.4 ms"),
                Label(0.0006000000000000001, "0.6 ms"),
                Label(0.0008, "0.8 ms"),
                Label(0.001, "1 ms"),
                Label(0.0012000000000000001, "1.2 ms"),
            ],
            id="time-small",
        ),
        pytest.param(
            TimeFormatter("s", metrics.AutoPrecision(2)),
            123456.789,
            "Time",
            [
                Label(21600, "6 h"),
                Label(43200, "12 h"),
                Label(64800, "18 h"),
                Label(86400, "24 h"),
                Label(108000, "30 h"),
            ],
            id="time-large",
        ),
        pytest.param(
            TimeFormatter("s", metrics.AutoPrecision(2)),
            86400001,
            "Time",
            [
                Label(17280000, "200 d"),
                Label(34560000, "400 d"),
                Label(51840000, "600 d"),
                Label(69120000, "800 d"),
                Label(86400000, "1000 d"),
            ],
            id="time-very-large",
        ),
    ],
)
def test_render_y_labels(
    formatter: (
        SIFormatter
        | IECFormatter
        | StandardScientificFormatter
        | EngineeringScientificFormatter
        | TimeFormatter
    ),
    max_y: int | float,
    expected_ident: Literal[
        "Decimal", "SI", "IEC", "StandardScientific", "EngineeringScientific", "Time"
    ],
    expected_labels: Sequence[Label],
) -> None:
    assert formatter.ident() == expected_ident
    assert formatter.render_y_labels(max_y, 5) == expected_labels

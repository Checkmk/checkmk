#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal

import pytest

from cmk.gui.graphing._formatter import (
    _stringify_small_decimal_number,
    AutoPrecision,
    DecimalFormatter,
    EngineeringScientificFormatter,
    IECFormatter,
    Label,
    NegativeYRange,
    NotationFormatter,
    PositiveYRange,
    SIFormatter,
    StandardScientificFormatter,
    StrictPrecision,
    TimeFormatter,
)


@pytest.mark.parametrize(
    "precision, value, expected",
    [
        pytest.param(
            AutoPrecision(digits=0),
            0,
            "0 unit",
            id="zero",
        ),
        pytest.param(
            AutoPrecision(digits=0),
            1,
            "1 unit",
            id="one",
        ),
        #
        pytest.param(
            AutoPrecision(digits=0),
            0.006789,
            "0.007 unit",
            id="small-zeros-auto-0",
        ),
        pytest.param(
            StrictPrecision(digits=0),
            0.006789,
            "0 unit",
            id="small-zeros-strict-0",
        ),
        pytest.param(
            AutoPrecision(digits=1),
            0.006789,
            "0.007 unit",
            id="small-zeros-auto-1",
        ),
        pytest.param(
            StrictPrecision(digits=1),
            0.006789,
            "0 unit",
            id="small-zeros-strict-1",
        ),
        pytest.param(
            AutoPrecision(digits=0),
            0.6789,
            "1 unit",
            id="small-no-zeros-auto-0",
        ),
        pytest.param(
            StrictPrecision(digits=0),
            0.6789,
            "1 unit",
            id="small-no-zeros-strict-0",
        ),
        pytest.param(
            AutoPrecision(digits=1),
            0.6789,
            "0.7 unit",
            id="small-no-zeros-auto-1",
        ),
        pytest.param(
            StrictPrecision(digits=1),
            0.6789,
            "0.7 unit",
            id="small-no-zeros-strict-1",
        ),
        #
        pytest.param(
            AutoPrecision(digits=0),
            12345.006789,
            "12 345.007 unit",
            id="large-zeros-auto-0",
        ),
        pytest.param(
            StrictPrecision(digits=0),
            12345.006789,
            "12 345 unit",
            id="large-zeros-strict-0",
        ),
        pytest.param(
            AutoPrecision(digits=1),
            12345.006789,
            "12 345.007 unit",
            id="large-zeros-auto-1",
        ),
        pytest.param(
            StrictPrecision(digits=1),
            12345.006789,
            "12 345 unit",
            id="large-zeros-strict-1",
        ),
        pytest.param(
            AutoPrecision(digits=0),
            12345.6789,
            "12 346 unit",
            id="large-no-zeros-auto-0",
        ),
        pytest.param(
            StrictPrecision(digits=0),
            12345.6789,
            "12 346 unit",
            id="large-no-zeros-strict-0",
        ),
        pytest.param(
            AutoPrecision(digits=1),
            12345.6789,
            "12 345.7 unit",
            id="large-no-zeros-auto-1",
        ),
        pytest.param(
            StrictPrecision(digits=1),
            12345.6789,
            "12 345.7 unit",
            id="large-no-zeros-strict-1",
        ),
    ],
)
def test_render_unit_precision(
    precision: AutoPrecision | StrictPrecision,
    value: int | float,
    expected: str,
) -> None:
    assert DecimalFormatter(symbol="unit", precision=precision).render(value) == expected


@pytest.mark.parametrize(
    "formatter, value, expected",
    [
        pytest.param(
            SIFormatter(
                symbol="unit",
                precision=StrictPrecision(digits=2),
            ),
            0.0000123456789,
            "12.35 μunit",
            id="si-small",
        ),
        pytest.param(
            SIFormatter(
                symbol="unit",
                precision=StrictPrecision(digits=2),
            ),
            123456.789,
            "123.46 kunit",
            id="si-large",
        ),
        pytest.param(
            SIFormatter(
                symbol="unit",
                precision=StrictPrecision(digits=2),
            ),
            999.999,
            "1000 unit",
            id="si-large-border",
        ),
        pytest.param(
            IECFormatter(
                symbol="unit",
                precision=StrictPrecision(digits=2),
            ),
            0.0000123456789,
            "0 unit",
            id="iec-small",
        ),
        pytest.param(
            IECFormatter(
                symbol="unit",
                precision=StrictPrecision(digits=2),
            ),
            123456.789,
            "120.56 Kiunit",
            id="iec-large",
        ),
        pytest.param(
            IECFormatter(
                symbol="unit",
                precision=StrictPrecision(digits=2),
            ),
            1023.999,
            "1024 unit",
            id="iec-large-border",
        ),
        pytest.param(
            StandardScientificFormatter(
                symbol="unit",
                precision=StrictPrecision(digits=2),
            ),
            0.0000123456789,
            "1.23e-5 unit",
            id="standard-scientific-small",
        ),
        pytest.param(
            StandardScientificFormatter(
                symbol="unit",
                precision=StrictPrecision(digits=2),
            ),
            123456.789,
            "1.23e+5 unit",
            id="standard-scientific-large",
        ),
        pytest.param(
            StandardScientificFormatter(
                symbol="unit",
                precision=StrictPrecision(digits=2),
            ),
            0.00001,
            "1e-5 unit",
            id="standard-scientific-small-power-of-ten",
        ),
        pytest.param(
            StandardScientificFormatter(
                symbol="unit",
                precision=StrictPrecision(digits=2),
            ),
            100000.0,
            "1e+5 unit",
            id="standard-scientific-large-power-of-ten",
        ),
        pytest.param(
            EngineeringScientificFormatter(
                symbol="unit",
                precision=StrictPrecision(digits=2),
            ),
            0.0000123456789,
            "12.35e-6 unit",
            id="engineering-scientific-small",
        ),
        pytest.param(
            EngineeringScientificFormatter(
                symbol="unit",
                precision=StrictPrecision(digits=2),
            ),
            123456.789,
            "123.46e+3 unit",
            id="engineering-scientific-large",
        ),
        pytest.param(
            EngineeringScientificFormatter(
                symbol="unit",
                precision=StrictPrecision(digits=2),
            ),
            0.00001,
            "10e-6 unit",
            id="engineering-scientific-small-power-of-ten",
        ),
        pytest.param(
            EngineeringScientificFormatter(
                symbol="unit",
                precision=StrictPrecision(digits=2),
            ),
            1000000.0,
            "1e+6 unit",
            id="engineering-scientific-large-power-of-ten",
        ),
        pytest.param(
            EngineeringScientificFormatter(
                symbol="unit",
                precision=StrictPrecision(digits=2),
            ),
            100000.0,
            "100e+3 unit",
            id="engineering-scientific-large-power-of-ten-2",
        ),
        pytest.param(
            EngineeringScientificFormatter(
                symbol="unit",
                precision=StrictPrecision(digits=2),
            ),
            120000.0,
            "120e+3 unit",
            id="engineering-scientific-large-power-of-ten-2",
        ),
        pytest.param(
            TimeFormatter(
                symbol="s",
                precision=StrictPrecision(digits=2),
            ),
            0.0000123456789,
            "12.35 μs",
            id="time-small",
        ),
        pytest.param(
            TimeFormatter(
                symbol="s",
                precision=StrictPrecision(digits=2),
            ),
            137,
            "2 min 17 s",
            id="time-minutes",
        ),
        pytest.param(
            TimeFormatter(
                symbol="s",
                precision=StrictPrecision(digits=2),
            ),
            4312,
            "1 h 12 min",
            id="time-hours",
        ),
        pytest.param(
            TimeFormatter(
                symbol="s",
                precision=StrictPrecision(digits=2),
            ),
            123456.789,
            "1 d 10 h",
            id="time-large",
        ),
        pytest.param(
            TimeFormatter(
                symbol="s",
                precision=StrictPrecision(digits=2),
            ),
            86399.999,
            "24 h",
            id="time-large-border",
        ),
        pytest.param(
            DecimalFormatter(
                symbol="/unit",
                precision=StrictPrecision(digits=2),
            ),
            2,
            "2/unit",
            id="unit-with-leading-slash",
        ),
        pytest.param(
            SIFormatter(
                symbol="/unit",
                precision=StrictPrecision(digits=2),
            ),
            2000,
            "2 k/unit",
            id="unit-with-leading-slash-but-prefix",
        ),
        pytest.param(
            TimeFormatter(
                symbol="s",
                precision=StrictPrecision(digits=2),
            ),
            31536000,
            "1 y",
            id="time-one-year",
        ),
        pytest.param(
            TimeFormatter(
                symbol="s",
                precision=StrictPrecision(digits=2),
            ),
            47304000,
            "1 y 182 d",
            id="time-one-and-a-half-year",
        ),
        pytest.param(
            TimeFormatter(
                symbol="s",
                precision=StrictPrecision(digits=2),
            ),
            315360000,
            "10 y",
            id="time-ten-years",
        ),
    ],
)
def test_render_unit_notation(
    formatter: NotationFormatter,
    value: int | float,
    expected: str,
) -> None:
    assert formatter.render(value) == expected


@pytest.mark.parametrize(
    "formatter, y_range, expected_ident, expected_labels",
    [
        pytest.param(
            DecimalFormatter("u", AutoPrecision(digits=2)),
            PositiveYRange(start=0.0, end=0.00123),
            "Decimal",
            [
                Label(0, "0"),
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
            DecimalFormatter("u", AutoPrecision(digits=2)),
            PositiveYRange(start=0.0, end=123456.789),
            "Decimal",
            [
                Label(0, "0"),
                Label(20000, "20 000 u"),
                Label(40000, "40 000 u"),
                Label(60000, "60 000 u"),
                Label(80000, "80 000 u"),
                Label(100000, "100 000 u"),
                Label(120000, "120 000 u"),
            ],
            id="decimal-large",
        ),
        pytest.param(
            DecimalFormatter("u", AutoPrecision(digits=2)),
            NegativeYRange(start=-11.19, end=-2.123),
            "Decimal",
            [
                Label(-2.0, "-2 u"),
                Label(-4.0, "-4 u"),
                Label(-6.0, "-6 u"),
                Label(-8.0, "-8 u"),
                Label(-10.0, "-10 u"),
            ],
            id="decimal-negative",
        ),
        pytest.param(
            SIFormatter("u", AutoPrecision(digits=2)),
            PositiveYRange(start=0.0, end=0.00123),
            "SI",
            [
                Label(0, "0"),
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
            SIFormatter("u", AutoPrecision(digits=2)),
            PositiveYRange(start=0.0, end=123456.789),
            "SI",
            [
                Label(0, "0"),
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
            SIFormatter("u", AutoPrecision(digits=2)),
            NegativeYRange(start=-1.12e5, end=-423),
            "SI",
            [
                Label(0, "0"),
                Label(-20000, "-20 ku"),
                Label(-40000, "-40 ku"),
                Label(-60000, "-60 ku"),
                Label(-80000, "-80 ku"),
                Label(-100000, "-100 ku"),
            ],
            id="si-negative",
        ),
        pytest.param(
            IECFormatter("u", AutoPrecision(digits=2)),
            PositiveYRange(start=0.0, end=0.00123),
            "IEC",
            [
                Label(0, "0"),
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
            IECFormatter("u", AutoPrecision(digits=2)),
            PositiveYRange(start=0.0, end=123456.789),
            "IEC",
            [
                Label(0, "0"),
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
            IECFormatter("u", AutoPrecision(digits=2)),
            NegativeYRange(start=-0.144, end=-4.432e-4),
            "IEC",
            [
                Label(0, "0"),
                Label(-0.02, "-0.02 u"),
                Label(-0.04, "-0.04 u"),
                Label(-0.06, "-0.06 u"),
                Label(-0.08, "-0.08 u"),
                Label(-0.1, "-0.1 u"),
                Label(-0.12, "-0.12 u"),
                Label(-0.14, "-0.14 u"),
            ],
            id="iec-negative",
        ),
        pytest.param(
            StandardScientificFormatter("u", AutoPrecision(digits=2)),
            PositiveYRange(start=0.0, end=0.00123),
            "StandardScientific",
            [
                Label(0, "0"),
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
            StandardScientificFormatter("u", AutoPrecision(digits=2)),
            PositiveYRange(start=0.0, end=123456.789),
            "StandardScientific",
            [
                Label(0, "0"),
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
            StandardScientificFormatter("u", AutoPrecision(digits=2)),
            NegativeYRange(start=-5e10, end=-1e10),
            "StandardScientific",
            [
                Label(-10000000000, "-1e+10 u"),
                Label(-20000000000, "-2e+10 u"),
                Label(-30000000000, "-3e+10 u"),
                Label(-40000000000, "-4e+10 u"),
                Label(-50000000000, "-5e+10 u"),
            ],
            id="std-sci-negative",
        ),
        pytest.param(
            EngineeringScientificFormatter("u", AutoPrecision(digits=2)),
            PositiveYRange(start=0.0, end=0.00123),
            "EngineeringScientific",
            [
                Label(0, "0"),
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
            EngineeringScientificFormatter("u", AutoPrecision(digits=2)),
            PositiveYRange(start=0.0, end=123456.789),
            "EngineeringScientific",
            [
                Label(0, "0"),
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
            EngineeringScientificFormatter("u", AutoPrecision(digits=2)),
            NegativeYRange(start=-5e10, end=-1e2),
            "EngineeringScientific",
            [
                Label(0, "0"),
                Label(-10000000000, "-10e+9 u"),
                Label(-20000000000, "-20e+9 u"),
                Label(-30000000000, "-30e+9 u"),
                Label(-40000000000, "-40e+9 u"),
                Label(-50000000000, "-50e+9 u"),
            ],
            id="eng-sci-negative",
        ),
        pytest.param(
            TimeFormatter("s", AutoPrecision(digits=2)),
            PositiveYRange(start=0.0, end=0.00123),
            "Time",
            [
                Label(0, "0"),
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
            TimeFormatter("s", AutoPrecision(digits=2)),
            PositiveYRange(start=0.0, end=123456.789),
            "Time",
            [
                Label(0, "0"),
                Label(21600, "6 h"),
                Label(43200, "12 h"),
                Label(64800, "18 h"),
                Label(86400, "24 h"),
                Label(108000, "30 h"),
            ],
            id="time-large",
        ),
        pytest.param(
            TimeFormatter("s", AutoPrecision(digits=2)),
            PositiveYRange(start=0, end=31536001),
            "Time",
            [
                Label(0, "0"),
                Label(4320000, "50 d"),
                Label(8640000, "100 d"),
                Label(12960000, "150 d"),
                Label(17280000, "200 d"),
                Label(21600000, "250 d"),
                Label(25920000, "300 d"),
                Label(30240000, "350 d"),
            ],
            id="time->year",
        ),
        pytest.param(
            TimeFormatter("s", AutoPrecision(digits=2)),
            PositiveYRange(start=0.0, end=15552000.123),
            "Time",
            [
                Label(0, "0"),
                Label(4320000, "50 d"),
                Label(8640000, "100 d"),
                Label(12960000, "150 d"),
            ],
            id="time-half-year",
        ),
        pytest.param(
            TimeFormatter("s", AutoPrecision(digits=2)),
            PositiveYRange(start=0, end=94608000),
            "Time",
            [
                Label(0, "0"),
                Label(31536000, "1 y"),
                Label(63072000, "2 y"),
                Label(94608000, "3 y"),
            ],
            id="time-three-years",
        ),
        pytest.param(
            TimeFormatter("s", AutoPrecision(digits=2)),
            PositiveYRange(start=0, end=315360000),
            "Time",
            [
                Label(0, "0"),
                Label(63072000, "2 y"),
                Label(126144000, "4 y"),
                Label(189216000, "6 y"),
                Label(252288000, "8 y"),
                Label(315360000, "10 y"),
            ],
            id="time-ten-years",
        ),
        pytest.param(
            TimeFormatter("s", AutoPrecision(digits=2)),
            NegativeYRange(start=-10.123, end=-5.11),
            "Time",
            [
                Label(-5, "-5 s"),
                Label(-6, "-6 s"),
                Label(-7, "-7 s"),
                Label(-8, "-8 s"),
                Label(-9, "-9 s"),
                Label(-10, "-10 s"),
            ],
            id="time-negative-small",
        ),
        pytest.param(
            TimeFormatter("s", AutoPrecision(digits=2)),
            NegativeYRange(start=-25552000.123, end=-15552000.123),
            "Time",
            [
                Label(-15552000, "-180 d"),
                Label(-17280000, "-200 d"),
                Label(-19008000, "-220 d"),
                Label(-20736000, "-240 d"),
                Label(-22464000, "-260 d"),
                Label(-24192000, "-280 d"),
            ],
            id="time-negative-large",
        ),
    ],
)
def test_render_y_labels(
    formatter: (
        DecimalFormatter
        | SIFormatter
        | IECFormatter
        | StandardScientificFormatter
        | EngineeringScientificFormatter
        | TimeFormatter
    ),
    y_range: PositiveYRange | NegativeYRange,
    expected_ident: Literal[
        "Decimal", "SI", "IEC", "StandardScientific", "EngineeringScientific", "Time"
    ],
    expected_labels: Sequence[Label],
) -> None:
    assert formatter.ident() == expected_ident
    assert formatter.render_y_labels(y_range, target_number_of_labels=5) == expected_labels


@pytest.mark.parametrize(
    "y_range, expected_labels",
    [
        pytest.param(
            PositiveYRange(start=0.00123, end=0.00456),
            [
                Label(0, "0"),
                Label(0.001, "0.001 u"),
                Label(0.002, "0.002 u"),
                Label(0.003, "0.003 u"),
                Label(0.004, "0.004 u"),
            ],
            id="decimal-small",
        ),
        pytest.param(
            PositiveYRange(start=123.456, end=456.789),
            [
                Label(100, "100 u"),
                Label(150, "150 u"),
                Label(200, "200 u"),
                Label(250, "250 u"),
                Label(300, "300 u"),
                Label(350, "350 u"),
                Label(400, "400 u"),
                Label(450, "450 u"),
            ],
            id="decimal-large",
        ),
        pytest.param(
            NegativeYRange(start=-456.789, end=-123.456),
            [
                Label(-100, "-100 u"),
                Label(-150, "-150 u"),
                Label(-200, "-200 u"),
                Label(-250, "-250 u"),
                Label(-300, "-300 u"),
                Label(-350, "-350 u"),
                Label(-400, "-400 u"),
                Label(-450, "-450 u"),
            ],
            id="decimal-negative",
        ),
    ],
)
def test_decimal_render_y_labels_with_min_y(
    y_range: PositiveYRange | NegativeYRange,
    expected_labels: Sequence[Label],
) -> None:
    assert (
        DecimalFormatter("u", AutoPrecision(digits=2)).render_y_labels(
            y_range,
            target_number_of_labels=5,
        )
        == expected_labels
    )


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(
            0.1023,
            "0.1023",
            id="10",
        ),
        pytest.param(
            0.01023,
            "0.01023",
            id="100",
        ),
        pytest.param(
            0.001023,
            "0.001023",
            id="1000",
        ),
        pytest.param(
            0.0001023,
            "0.0001023",
            id="10000",
        ),
        pytest.param(
            0.00001023,
            "0.00001023",
            id="pythons-sci-format-100000",
        ),
        pytest.param(
            0.000001023,
            "0.000001023",
            id="pythons-sci-format-1000000",
        ),
    ],
)
def test__stringify_small_decimal_number(value: float, expected: str) -> None:
    assert _stringify_small_decimal_number(value) == expected

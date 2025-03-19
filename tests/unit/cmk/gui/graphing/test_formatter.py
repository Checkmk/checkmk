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
    NotationFormatter,
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
    "formatter, max_y, expected_ident, expected_labels",
    [
        pytest.param(
            DecimalFormatter("u", AutoPrecision(digits=2)),
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
            DecimalFormatter("u", AutoPrecision(digits=2)),
            123456.789,
            "Decimal",
            [
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
            SIFormatter("u", AutoPrecision(digits=2)),
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
            SIFormatter("u", AutoPrecision(digits=2)),
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
            IECFormatter("u", AutoPrecision(digits=2)),
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
            IECFormatter("u", AutoPrecision(digits=2)),
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
            StandardScientificFormatter("u", AutoPrecision(digits=2)),
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
            StandardScientificFormatter("u", AutoPrecision(digits=2)),
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
            EngineeringScientificFormatter("u", AutoPrecision(digits=2)),
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
            EngineeringScientificFormatter("u", AutoPrecision(digits=2)),
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
            TimeFormatter("s", AutoPrecision(digits=2)),
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
            TimeFormatter("s", AutoPrecision(digits=2)),
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
            TimeFormatter("s", AutoPrecision(digits=2)),
            31536001,
            "Time",
            [
                Label(position=4320000, text="50 d"),
                Label(position=8640000, text="100 d"),
                Label(position=12960000, text="150 d"),
                Label(position=17280000, text="200 d"),
                Label(position=21600000, text="250 d"),
                Label(position=25920000, text="300 d"),
                Label(position=30240000, text="350 d"),
            ],
            id="time->year",
        ),
        pytest.param(
            TimeFormatter("s", AutoPrecision(digits=2)),
            15552000.123,
            "Time",
            [
                Label(position=4320000, text="50 d"),
                Label(position=8640000, text="100 d"),
                Label(position=12960000, text="150 d"),
            ],
            id="time-half-year",
        ),
        pytest.param(
            TimeFormatter("s", AutoPrecision(digits=2)),
            94608000,
            "Time",
            [
                Label(position=31536000, text="1 y"),
                Label(position=63072000, text="2 y"),
                Label(position=94608000, text="3 y"),
            ],
            id="time-three-years",
        ),
        pytest.param(
            TimeFormatter("s", AutoPrecision(digits=2)),
            315360000,
            "Time",
            [
                Label(position=63072000, text="2 y"),
                Label(position=126144000, text="4 y"),
                Label(position=189216000, text="6 y"),
                Label(position=252288000, text="8 y"),
                Label(position=315360000, text="10 y"),
            ],
            id="time-ten-years",
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
    max_y: int | float,
    expected_ident: Literal[
        "Decimal", "SI", "IEC", "StandardScientific", "EngineeringScientific", "Time"
    ],
    expected_labels: Sequence[Label],
) -> None:
    assert formatter.ident() == expected_ident
    assert formatter.render_y_labels(min_y=0, max_y=max_y, mean_num_labels=5) == expected_labels


@pytest.mark.parametrize(
    "min_y, max_y, expected_labels",
    [
        pytest.param(
            0.00123,
            0.00456,
            [
                Label(
                    position=0.001,
                    text="0.001 u",
                ),
                Label(
                    position=0.002,
                    text="0.002 u",
                ),
                Label(
                    position=0.003,
                    text="0.003 u",
                ),
                Label(
                    position=0.004,
                    text="0.004 u",
                ),
            ],
            id="decimal-small",
        ),
        pytest.param(
            123.456,
            456.789,
            [
                Label(
                    position=123,
                    text="123 u",
                ),
                Label(
                    position=173,
                    text="173 u",
                ),
                Label(
                    position=223,
                    text="223 u",
                ),
                Label(
                    position=273,
                    text="273 u",
                ),
                Label(
                    position=323,
                    text="323 u",
                ),
                Label(
                    position=373,
                    text="373 u",
                ),
                Label(
                    position=423,
                    text="423 u",
                ),
            ],
            id="decimal-large",
        ),
    ],
)
def test_decimal_render_y_labels_with_min_y(
    min_y: float, max_y: float, expected_labels: Sequence[Label]
) -> None:
    assert (
        DecimalFormatter("u", AutoPrecision(digits=2)).render_y_labels(
            min_y=min_y,
            max_y=max_y,
            mean_num_labels=5,
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

#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.graphing._parser import parse_or_add_unit

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
            100000.0,
            "100e+3 unit",
            id="engineering-scientific-large-power-of-ten",
        ),
        pytest.param(
            metrics.TimeNotation(),
            0.0000123456789,
            "12.35 µs",
            id="time-small",
        ),
        pytest.param(
            metrics.TimeNotation(),
            123456.789,
            "1.43 d",
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
            """v => cmk.number_format.render(
    v,
    new cmk.number_format.NotationFormatter(
        "unit",
        new cmk.number_format.AutoPrecision(2),
        cmk.number_format.preformat_number,
        cmk.number_format.preformat_number,
    )
)""",
            id="decimal-auto",
        ),
        pytest.param(
            metrics.Unit(metrics.DecimalNotation("unit"), metrics.StrictPrecision(2)),
            """v => cmk.number_format.render(
    v,
    new cmk.number_format.NotationFormatter(
        "unit",
        new cmk.number_format.StrictPrecision(2),
        cmk.number_format.preformat_number,
        cmk.number_format.preformat_number,
    )
)""",
            id="decimal-strict",
        ),
        #
        pytest.param(
            metrics.Unit(metrics.SINotation("unit"), metrics.AutoPrecision(2)),
            """v => cmk.number_format.render(
    v,
    new cmk.number_format.NotationFormatter(
        "unit",
        new cmk.number_format.AutoPrecision(2),
        cmk.number_format.si_preformat_small_number,
        cmk.number_format.si_preformat_large_number,
    )
)""",
            id="si-auto",
        ),
        pytest.param(
            metrics.Unit(metrics.SINotation("unit"), metrics.StrictPrecision(2)),
            """v => cmk.number_format.render(
    v,
    new cmk.number_format.NotationFormatter(
        "unit",
        new cmk.number_format.StrictPrecision(2),
        cmk.number_format.si_preformat_small_number,
        cmk.number_format.si_preformat_large_number,
    )
)""",
            id="si-strict",
        ),
        #
        pytest.param(
            metrics.Unit(metrics.IECNotation("unit"), metrics.AutoPrecision(2)),
            """v => cmk.number_format.render(
    v,
    new cmk.number_format.NotationFormatter(
        "unit",
        new cmk.number_format.AutoPrecision(2),
        cmk.number_format.preformat_number,
        cmk.number_format.iec_preformat_large_number,
    )
)""",
            id="iec-auto",
        ),
        pytest.param(
            metrics.Unit(metrics.IECNotation("unit"), metrics.StrictPrecision(2)),
            """v => cmk.number_format.render(
    v,
    new cmk.number_format.NotationFormatter(
        "unit",
        new cmk.number_format.StrictPrecision(2),
        cmk.number_format.preformat_number,
        cmk.number_format.iec_preformat_large_number,
    )
)""",
            id="iec-strict",
        ),
        #
        pytest.param(
            metrics.Unit(metrics.StandardScientificNotation("unit"), metrics.AutoPrecision(2)),
            """v => cmk.number_format.render(
    v,
    new cmk.number_format.NotationFormatter(
        "unit",
        new cmk.number_format.AutoPrecision(2),
        cmk.number_format.standard_scientific_preformat_small_number,
        cmk.number_format.standard_scientific_preformat_large_number,
    )
)""",
            id="standard-scientific-auto",
        ),
        pytest.param(
            metrics.Unit(metrics.StandardScientificNotation("unit"), metrics.StrictPrecision(2)),
            """v => cmk.number_format.render(
    v,
    new cmk.number_format.NotationFormatter(
        "unit",
        new cmk.number_format.StrictPrecision(2),
        cmk.number_format.standard_scientific_preformat_small_number,
        cmk.number_format.standard_scientific_preformat_large_number,
    )
)""",
            id="standard-scientific-strict",
        ),
        #
        pytest.param(
            metrics.Unit(metrics.EngineeringScientificNotation("unit"), metrics.AutoPrecision(2)),
            """v => cmk.number_format.render(
    v,
    new cmk.number_format.NotationFormatter(
        "unit",
        new cmk.number_format.AutoPrecision(2),
        cmk.number_format.engineering_scientific_preformat_small_number,
        cmk.number_format.engineering_scientific_preformat_large_number,
    )
)""",
            id="engineering-scientific-auto",
        ),
        pytest.param(
            metrics.Unit(metrics.EngineeringScientificNotation("unit"), metrics.StrictPrecision(2)),
            """v => cmk.number_format.render(
    v,
    new cmk.number_format.NotationFormatter(
        "unit",
        new cmk.number_format.StrictPrecision(2),
        cmk.number_format.engineering_scientific_preformat_small_number,
        cmk.number_format.engineering_scientific_preformat_large_number,
    )
)""",
            id="engineering-scientific-strict",
        ),
        #
        pytest.param(
            metrics.Unit(metrics.TimeNotation(), metrics.AutoPrecision(2)),
            """v => cmk.number_format.render(
    v,
    new cmk.number_format.NotationFormatter(
        "s",
        new cmk.number_format.AutoPrecision(2),
        cmk.number_format.time_preformat_small_number,
        cmk.number_format.time_preformat_large_number,
    )
)""",
            id="time-auto",
        ),
        pytest.param(
            metrics.Unit(metrics.TimeNotation(), metrics.StrictPrecision(2)),
            """v => cmk.number_format.render(
    v,
    new cmk.number_format.NotationFormatter(
        "s",
        new cmk.number_format.StrictPrecision(2),
        cmk.number_format.time_preformat_small_number,
        cmk.number_format.time_preformat_large_number,
    )
)""",
            id="time-strict",
        ),
    ],
)
def test_js_render_unit_notation(unit: metrics.Unit, expected: str) -> None:
    assert parse_or_add_unit(unit)["js_render"] == expected

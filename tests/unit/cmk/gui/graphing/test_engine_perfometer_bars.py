#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest

from cmk.graphing_engine import (
    AutoPrecision,
    CurveAttributes,
    DecimalNotation,
    EvaluatedBidirectional,
    EvaluatedFocusBound,
    EvaluatedFocusRange,
    EvaluatedPerfometer,
    EvaluatedPerfometerLayout,
    EvaluatedSegment,
    EvaluatedStacked,
    FocusBoundKind,
    Unit,
)
from cmk.gui.graphing import (
    drawn_segments,
    DrawnSegment,
    perfometer_label,
    perfometer_sort_value,
)
from cmk.gui.utils.temperate_unit import TemperatureUnit

_UNIT = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))


def _closed(value: float) -> EvaluatedFocusBound:
    return EvaluatedFocusBound(bound_kind=FocusBoundKind.CLOSED, value=value)


def _open(value: float) -> EvaluatedFocusBound:
    return EvaluatedFocusBound(bound_kind=FocusBoundKind.OPEN, value=value)


def _segment(value: float, color: str = "#111111", unit: Unit = _UNIT) -> EvaluatedSegment:
    return EvaluatedSegment(
        value=value, attributes=CurveAttributes(title="Segment", unit=unit, color=color)
    )


def _bar(
    *segments: EvaluatedSegment,
    lower: EvaluatedFocusBound | None = None,
    upper: EvaluatedFocusBound | None = None,
    name: str = "p",
) -> EvaluatedPerfometer:
    return EvaluatedPerfometer(
        name=name,
        focus_range=EvaluatedFocusRange(
            lower=lower if lower is not None else _closed(0.0),
            upper=upper if upper is not None else _closed(100.0),
        ),
        segments=list(segments),
    )


def _fill_level(value: float, lower: EvaluatedFocusBound, upper: EvaluatedFocusBound) -> float:
    (row,) = drawn_segments(_bar(_segment(value), lower=lower, upper=upper))
    return row[0].share


@pytest.mark.parametrize(
    "lower, upper, value, share",
    [
        pytest.param(_closed(-10.0), _closed(20.0), -10, 0.0, id="closed-closed left"),
        pytest.param(_closed(-10.0), _closed(20.0), 5, 50.0, id="closed-closed middle"),
        pytest.param(_closed(-10.0), _closed(20.0), 20, 100.0, id="closed-closed right"),
        pytest.param(_closed(-10.0), _closed(20.0), -11, 0.0, id="closed-closed below"),
        pytest.param(_closed(-10.0), _closed(20.0), 21, 100.0, id="closed-closed above"),
        pytest.param(_open(-10.0), _closed(20.0), -11, 12.25, id="open-closed below"),
        pytest.param(_open(-10.0), _closed(20.0), -10, 15.0, id="open-closed left"),
        pytest.param(_open(-10.0), _closed(20.0), 5, 57.5, id="open-closed middle"),
        pytest.param(_open(-10.0), _closed(20.0), 20, 100.0, id="open-closed right"),
        pytest.param(_open(-10.0), _closed(20.0), 21, 100.0, id="open-closed above"),
        pytest.param(_closed(-10.0), _open(20.0), -11, 0.0, id="closed-open below"),
        pytest.param(_closed(-10.0), _open(20.0), -10, 0.0, id="closed-open left"),
        pytest.param(_closed(-10.0), _open(20.0), 5, 42.5, id="closed-open middle"),
        pytest.param(_closed(-10.0), _open(20.0), 20, 85.0, id="closed-open right"),
        pytest.param(_closed(-10.0), _open(20.0), 21, 87.75, id="closed-open above"),
        pytest.param(_open(-10.0), _open(20.0), -11, 12.71, id="open-open below"),
        pytest.param(_open(-10.0), _open(20.0), -10, 15.0, id="open-open left"),
        pytest.param(_open(-10.0), _open(20.0), 5, 50.0, id="open-open middle"),
        pytest.param(_open(-10.0), _open(20.0), 20, 85.0, id="open-open right"),
        pytest.param(_open(-10.0), _open(20.0), 21, 87.29, id="open-open above"),
    ],
)
def test_fill_level_of_a_bar(
    lower: EvaluatedFocusBound, upper: EvaluatedFocusBound, value: float, share: float
) -> None:
    assert _fill_level(value, lower, upper) == share


@pytest.mark.parametrize(
    "upper, value",
    [
        pytest.param(8.4e9, 9.0e9, id="a byte count"),
        pytest.param(50.0, 80.0, id="half a percent scale"),
        pytest.param(1.0, 2.0, id="a fraction"),
    ],
)
def test_fill_level_beyond_any_closed_upper_bound_is_a_full_bar(upper: float, value: float) -> None:
    assert _fill_level(value, _closed(0.0), _closed(upper)) == 100.0


def test_fill_level_of_a_bidirectional_half_fills_only_that_half() -> None:
    (row,) = drawn_segments(
        EvaluatedBidirectional(
            name="both",
            left=_bar(_segment(0.0), upper=_closed(100.0), name="l"),
            right=_bar(_segment(150.0), upper=_closed(100.0), name="r"),
        )
    )
    assert [segment.share for segment in row if segment.color is not None] == [0.0, 50.0]


@pytest.mark.parametrize(
    "layout, shares",
    [
        pytest.param(
            _bar(_segment(9.0e9), upper=_closed(8.4e9)),
            [[100.0, 0.0]],
            id="perfometer",
        ),
        pytest.param(
            EvaluatedBidirectional(
                name="both",
                left=_bar(_segment(9.0e9), upper=_closed(8.4e9), name="l"),
                right=_bar(_segment(9.0e9), upper=_closed(8.4e9), name="r"),
            ),
            [[0.0, 50.0, 50.0, 0.0]],
            id="bidirectional",
        ),
        pytest.param(
            EvaluatedStacked(
                name="stack",
                lower=_bar(_segment(9.0e9), upper=_closed(8.4e9), name="lo"),
                upper=_bar(_segment(9.0e9), upper=_closed(8.4e9), name="up"),
            ),
            [[100.0, 0.0], [100.0, 0.0]],
            id="stacked",
        ),
    ],
)
def test_every_drawn_row_is_filled_within_its_bounds(
    layout: EvaluatedPerfometerLayout, shares: Sequence[Sequence[float]]
) -> None:
    assert [[segment.share for segment in row] for row in drawn_segments(layout)] == shares


def test_drawn_segments_shares_the_fill_and_leaves_the_rest_uncoloured() -> None:
    rows = drawn_segments(_bar(_segment(30.0, "#aaaaaa"), _segment(10.0, "#bbbbbb")))
    assert rows == [
        [
            DrawnSegment(share=30.0, color="#aaaaaa"),
            DrawnSegment(share=10.0, color="#bbbbbb"),
            DrawnSegment(share=60.0, color=None),
        ]
    ]


def test_drawn_segments_of_equal_values_splits_the_fill_evenly() -> None:
    rows = drawn_segments(_bar(_segment(25.0, "#aaaaaa"), _segment(25.0, "#bbbbbb")))
    assert [segment.share for segment in rows[0]] == [25.0, 25.0, 50.0]


def test_drawn_segments_of_a_value_beyond_a_closed_end_fills_the_bar() -> None:
    rows = drawn_segments(_bar(_segment(500.0)))
    assert rows == [
        [DrawnSegment(share=100.0, color="#111111"), DrawnSegment(share=0.0, color=None)]
    ]


@pytest.mark.parametrize(
    "lower, upper",
    [
        pytest.param(_closed(10.0), _closed(-10.0), id="closed-closed"),
        pytest.param(_open(10.0), _closed(-10.0), id="open-closed"),
        pytest.param(_closed(10.0), _open(-10.0), id="closed-open"),
        pytest.param(_open(10.0), _open(-10.0), id="open-open"),
        pytest.param(_closed(0.0), _closed(0.0), id="closed-closed-equal"),
    ],
)
def test_drawn_segments_of_a_degenerate_range_is_one_empty_run(
    lower: EvaluatedFocusBound, upper: EvaluatedFocusBound
) -> None:
    rows = drawn_segments(_bar(_segment(5.0), lower=lower, upper=upper))
    assert rows == [[DrawnSegment(share=0.0, color=None)]]


def test_drawn_segments_of_a_bidirectional_is_one_row_growing_outwards() -> None:
    rows = drawn_segments(
        EvaluatedBidirectional(
            name="both",
            left=_bar(_segment(50.0, "#aaaaaa"), name="l"),
            right=_bar(_segment(25.0, "#bbbbbb"), name="r"),
        )
    )
    assert rows == [
        [
            DrawnSegment(share=25.0, color=None),
            DrawnSegment(share=25.0, color="#aaaaaa"),
            DrawnSegment(share=12.5, color="#bbbbbb"),
            DrawnSegment(share=37.5, color=None),
        ]
    ]


def test_drawn_segments_of_a_stacked_is_two_rows_upper_first() -> None:
    rows = drawn_segments(
        EvaluatedStacked(
            name="two",
            upper=_bar(_segment(30.0, "#aaaaaa"), name="up"),
            lower=_bar(_segment(10.0, "#bbbbbb"), name="lo"),
        )
    )
    assert [segment.color for row in rows for segment in row] == [
        "#aaaaaa",
        None,
        "#bbbbbb",
        None,
    ]
    assert [rows[0][0].share, rows[1][0].share] == [30.0, 10.0]


def test_label_of_a_bar_sums_its_segments() -> None:
    label = perfometer_label(_bar(_segment(30.0), _segment(12.0)), TemperatureUnit.CELSIUS)
    assert label == "42"


def test_label_of_a_bar_uses_the_first_segments_unit() -> None:
    percent = Unit(notation=DecimalNotation("%"), precision=AutoPrecision(2))
    label = perfometer_label(_bar(_segment(42.0, unit=percent)), TemperatureUnit.CELSIUS)
    assert label == "42 %"


def test_label_of_a_bidirectional_joins_both_halves() -> None:
    label = perfometer_label(
        EvaluatedBidirectional(
            name="both", left=_bar(_segment(1.0), name="l"), right=_bar(_segment(2.0), name="r")
        ),
        TemperatureUnit.CELSIUS,
    )
    assert label == "1 / 2"


def test_label_of_a_stacked_joins_upper_before_lower() -> None:
    label = perfometer_label(
        EvaluatedStacked(
            name="two", upper=_bar(_segment(1.0), name="up"), lower=_bar(_segment(2.0), name="lo")
        ),
        TemperatureUnit.CELSIUS,
    )
    assert label == "1 / 2"


def test_label_converts_to_the_users_temperature_unit() -> None:
    celsius = Unit(notation=DecimalNotation("°C"), precision=AutoPrecision(2))
    bar = _bar(_segment(20.0, unit=celsius))
    assert perfometer_label(bar, TemperatureUnit.CELSIUS) == "20 °C"
    assert perfometer_label(bar, TemperatureUnit.FAHRENHEIT) == "68 °F"


def test_the_fill_level_does_not_depend_on_the_temperature_unit() -> None:
    celsius = Unit(notation=DecimalNotation("°C"), precision=AutoPrecision(2))
    bar = _bar(_segment(20.0, unit=celsius))
    assert drawn_segments(bar)[0][0].share == 20.0


def test_sort_value_of_a_bar_sums_its_segments() -> None:
    assert perfometer_sort_value(_bar(_segment(30.0), _segment(12.0))) == 42.0


def test_sort_value_of_a_bidirectional_is_the_larger_half() -> None:
    assert (
        perfometer_sort_value(
            EvaluatedBidirectional(
                name="both", left=_bar(_segment(1.0), name="l"), right=_bar(_segment(7.0), name="r")
            )
        )
        == 7.0
    )


def test_sort_value_of_a_stacked_is_the_upper_bar() -> None:
    assert (
        perfometer_sort_value(
            EvaluatedStacked(
                name="two",
                upper=_bar(_segment(1.0), name="up"),
                lower=_bar(_segment(7.0), name="lo"),
            )
        )
        == 1.0
    )

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from zoneinfo import ZoneInfo

from cmk.graphing_engine import (
    AutoPrecision,
    CurveAttributes,
    DecimalNotation,
    EvaluatedCurve,
    EvaluatedGraph,
    EvaluatedLine,
    EvaluatedRegion,
    EvaluatedRule,
    EvaluatedStack,
    EvaluatedVerticalRange,
    TimeRange,
    TimeSeries,
    Unit,
    VerticalRangeKind,
)
from cmk.gui.png import compute_png_size_mm, PngGraph, PngOptions, PngTexts
from cmk.gui.png._drawing import png_drawing
from cmk.gui.png._size import _MM_PER_INCH
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.png_renderer import PngDrawing, TimeAxis

_UNIT = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))
_TIME_RANGE = TimeRange(start=0, end=180, step=60)
_TEXTS = PngTexts(
    minimum="Min",
    maximum="Max",
    average="Average",
    last="Last",
    date_format="%Y-%m-%d",
    caption="for %(date_range)s, resolution: %(resolution)s",
)
_CELSIUS = Unit(notation=DecimalNotation("°C"), precision=AutoPrecision(2))
_FAHRENHEIT = Unit(notation=DecimalNotation("°F"), precision=AutoPrecision(2))


def _options(*, shown: bool = True) -> PngOptions:
    return PngOptions(
        size=(70.0, 16.0),
        font_size=8.0,
        show_title=shown,
        show_legend=shown,
        show_vertical_axis=shown,
        show_time_axis=shown,
        show_graph_time=shown,
    )


def _curve(
    title: str,
    values: list[float | None],
    *,
    time_range: TimeRange = _TIME_RANGE,
    unit: Unit = _UNIT,
) -> EvaluatedCurve:
    return EvaluatedCurve(
        id=title,
        attributes=CurveAttributes(title=title, unit=unit, color="#000000"),
        value=None,
        time_series=TimeSeries(time_range=time_range, values=values),
    )


def _graph(
    *,
    stacks: list[EvaluatedStack] | None = None,
    lines: list[EvaluatedLine] | None = None,
    rules: list[EvaluatedRule] | None = None,
    regions: list[EvaluatedRegion] | None = None,
    time_range: TimeRange = _TIME_RANGE,
    vertical_range: EvaluatedVerticalRange | None = None,
) -> EvaluatedGraph:
    return EvaluatedGraph(
        name="g",
        title="Graph",
        time_range=time_range,
        vertical_range=vertical_range,
        stacks=stacks or [],
        lines=lines or [],
        rules=rules or [],
        regions=regions or [],
    )


def _drawing(
    graph: EvaluatedGraph,
    *,
    options: PngOptions | None = None,
    y_axis_unit: Unit | None = None,
    requested_vertical_range: EvaluatedVerticalRange | None = None,
    time_zone: ZoneInfo | None = None,
    visible_time_range: tuple[int, int] | None = None,
    temperature_unit: TemperatureUnit = TemperatureUnit.CELSIUS,
) -> PngDrawing:
    return png_drawing(
        PngGraph(
            graph=graph,
            options=options or _options(),
            y_axis_unit=y_axis_unit,
            requested_vertical_range=requested_vertical_range,
            time_zone=time_zone,
            visible_time_range=visible_time_range or (graph.time_range.start, graph.time_range.end),
        ),
        _TEXTS,
        temperature_unit,
    )


def _rule(value: float, *, unit: Unit = _UNIT) -> EvaluatedRule:
    return EvaluatedRule(
        id="crit",
        attributes=CurveAttributes(title="Crit", unit=unit, color="#ff0000"),
        value=value,
        inverse=False,
    )


def test_second_area_stacks_onto_the_first_not_onto_zero() -> None:
    stack = EvaluatedStack(
        members=[_curve("first", [1.0, 2.0, 3.0]), _curve("second", [10.0, 20.0, 30.0])],
        inverse=False,
    )

    drawing = _drawing(_graph(stacks=[stack]))

    assert drawing.areas[1].top == [11.0, 22.0, 33.0]


def test_mirrored_stack_is_drawn_below_zero() -> None:
    stack = EvaluatedStack(members=[_curve("m", [5.0, 5.0, 5.0])], inverse=True)

    drawing = _drawing(_graph(stacks=[stack]))

    assert drawing.areas[0].top == [-5.0, -5.0, -5.0]


def test_the_legend_shows_the_curves_own_maxima_not_their_stacked_position() -> None:
    stack = EvaluatedStack(
        members=[_curve("first", [1.0, 2.0, 3.0]), _curve("second", [10.0, 20.0, 30.0])],
        inverse=False,
    )

    drawing = _drawing(_graph(stacks=[stack]))

    assert drawing.legend is not None and [row.cells[2] for row in drawing.legend.curves] == [
        "30.00",
        "3.00",
    ]


def test_the_legend_shows_the_natural_values_of_a_mirrored_curve() -> None:
    stack = EvaluatedStack(members=[_curve("out", [10.0, 20.0, 30.0])], inverse=True)

    drawing = _drawing(_graph(stacks=[stack]))

    assert drawing.legend is not None and drawing.legend.curves[0].cells == [
        "out",
        "10.00",
        "30.00",
        "20.00",
        "30.00",
    ]


def test_mirrored_y_labels_repeat_the_positive_labels_below_zero() -> None:
    line = EvaluatedLine(curve=_curve("m", [1000.0, 2000.0, 1500.0]), inverse=True)

    drawing = _drawing(
        _graph(lines=[line]),
        y_axis_unit=Unit(notation=DecimalNotation("B"), precision=AutoPrecision(2)),
    )

    assert drawing.vertical_axis is not None and drawing.vertical_axis.labels is not None
    labels = drawing.vertical_axis.labels
    assert {-label.position: label.text for label in labels if label.position < 0} == {
        label.position: label.text for label in labels if label.position > 0
    }


def test_a_far_away_rule_is_not_drawn() -> None:
    stack = EvaluatedStack(members=[_curve("m", [1.0, 2.0, 3.0])], inverse=False)

    drawing = _drawing(_graph(stacks=[stack], rules=[_rule(100000.0)]))

    assert drawing.rules == []


def test_a_far_away_rule_does_not_stretch_the_vertical_axis() -> None:
    stack = EvaluatedStack(members=[_curve("m", [1.0, 2.0, 3.0])], inverse=False)

    drawing = _drawing(_graph(stacks=[stack], rules=[_rule(100000.0)]))

    assert drawing.y_range == (0.0, 3.0)


def test_the_vertical_axis_follows_the_stacked_top_not_each_members_own_maximum() -> None:
    stack = EvaluatedStack(
        members=[_curve("first", [10.0, 10.0, 10.0]), _curve("second", [20.0, 20.0, 20.0])],
        inverse=False,
    )

    drawing = _drawing(_graph(stacks=[stack]))

    assert drawing.y_range == (0.0, 30.0)


def test_a_mirrored_graph_gets_a_symmetric_vertical_axis() -> None:
    line = EvaluatedLine(curve=_curve("m", [2.0, 30.0, 30.0]), inverse=True)

    drawing = _drawing(_graph(lines=[line]))

    assert drawing.y_range == (-30.0, 30.0)


def test_a_graph_without_data_keeps_the_range_of_an_empty_plot() -> None:
    drawing = _drawing(_graph(lines=[EvaluatedLine(curve=_curve("m", [None] * 3), inverse=False)]))

    assert drawing.y_range == (-0.05, 0.05)


def test_a_fixed_range_open_at_the_bottom_ends_at_its_bound_without_data() -> None:
    line = EvaluatedLine(curve=_curve("m", [None, None, None]), inverse=False)

    drawing = _drawing(
        _graph(
            lines=[line],
            vertical_range=EvaluatedVerticalRange(
                range_kind=VerticalRangeKind.FIXED, lower=None, upper=100.0
            ),
        )
    )

    assert drawing.y_range == (99.0, 100.0)


def test_a_fixed_range_open_at_the_bottom_ends_at_its_bound_with_data_at_the_bound() -> None:
    line = EvaluatedLine(curve=_curve("m", [100.0, 100.0, 100.0]), inverse=False)

    drawing = _drawing(
        _graph(
            lines=[line],
            vertical_range=EvaluatedVerticalRange(
                range_kind=VerticalRangeKind.FIXED, lower=None, upper=100.0
            ),
        )
    )

    assert drawing.y_range == (99.0, 100.0)


def test_values_are_drawn_at_their_bucket_end_like_the_vue_graph() -> None:
    line = EvaluatedLine(curve=_curve("m", [1.0, 2.0, 3.0]), inverse=False)

    drawing = _drawing(_graph(lines=[line]))

    assert drawing.times == [60, 120, 180]


def test_neighbours_beyond_the_visible_range_stretch_the_vertical_axis_only_up_to_the_edges() -> (
    None
):
    time_range = TimeRange(start=0, end=240, step=60)
    line = EvaluatedLine(
        curve=_curve("m", [100.0, 2.0, 4.0, 100.0], time_range=time_range), inverse=False
    )

    # The line crosses the edges halfway between its samples at 60/120 and 180/240.
    drawing = _drawing(_graph(lines=[line], time_range=time_range), visible_time_range=(90, 210))

    assert drawing.y_range == (2.0, 52.0)


def test_a_region_without_a_lower_bound_reaches_down_to_the_bottom_of_the_axis() -> None:
    line = EvaluatedLine(curve=_curve("m", [1.0, 2.0, 3.0]), inverse=False)
    region = EvaluatedRegion(
        id="region-0",
        attributes=CurveAttributes(title="OK", unit=_UNIT, color="#15d1a0"),
        lower=None,
        upper=TimeSeries(time_range=_TIME_RANGE, values=[2.0, 2.0, 2.0]),
    )

    drawing = _drawing(_graph(lines=[line], regions=[region]))

    assert drawing.regions[0].lower == [1.0, 1.0, 1.0]


def test_the_caption_dates_the_range_in_the_given_time_zone() -> None:
    # 2026-09-28 23:00 UTC is already 2026-09-29 in Berlin.
    time_range = TimeRange(start=1790636400, end=1790640000, step=60)

    drawing = _drawing(_graph(time_range=time_range), time_zone=ZoneInfo("Europe/Berlin"))

    assert drawing.caption == "for 2026-09-29, resolution: 1 min"


def test_the_time_axis_is_labelled_in_the_given_time_zone() -> None:
    drawing = _drawing(_graph(), time_zone=ZoneInfo("Europe/Berlin"))

    assert drawing.time_axis == TimeAxis(time_zone="Europe/Berlin")


def test_hidden_parts_of_the_graph_are_left_out_of_the_drawing() -> None:
    stack = EvaluatedStack(members=[_curve("m", [1.0, 2.0, 3.0])], inverse=False)

    drawing = _drawing(_graph(stacks=[stack]), options=_options(shown=False))

    assert (
        drawing.title,
        drawing.caption,
        drawing.vertical_axis,
        drawing.time_axis,
        drawing.legend,
    ) == (None, None, None, None, None)


def test_the_drawing_has_the_size_that_reports_reserve_for_it() -> None:
    graph = _graph(
        stacks=[EvaluatedStack(members=[_curve("m", [1.0, 2.0, 3.0])], inverse=False)],
        rules=[_rule(2.5)],
    )

    drawing = _drawing(graph)

    assert (
        drawing.width_inches * _MM_PER_INCH,
        drawing.height_inches * _MM_PER_INCH,
    ) == compute_png_size_mm(graph, _options())


def _temperature_graph(unit: Unit, values: list[float | None], warning: float) -> EvaluatedGraph:
    return _graph(
        lines=[EvaluatedLine(curve=_curve("Temperature", values, unit=unit), inverse=False)],
        rules=[_rule(warning, unit=unit)],
    )


def test_a_celsius_graph_is_drawn_like_its_fahrenheit_twin_for_a_fahrenheit_user() -> None:
    celsius = _drawing(
        _temperature_graph(_CELSIUS, [0.0, 50.0, 100.0], 80.0),
        y_axis_unit=_CELSIUS,
        temperature_unit=TemperatureUnit.FAHRENHEIT,
    )

    fahrenheit = _drawing(
        _temperature_graph(_FAHRENHEIT, [32.0, 122.0, 212.0], 176.0),
        y_axis_unit=_FAHRENHEIT,
        temperature_unit=TemperatureUnit.FAHRENHEIT,
    )

    assert celsius == fahrenheit


def test_a_requested_vertical_range_is_taken_in_the_users_unit() -> None:
    requested = EvaluatedVerticalRange(range_kind=VerticalRangeKind.FIXED, lower=50.0, upper=100.0)
    celsius = _drawing(
        _temperature_graph(_CELSIUS, [0.0, 50.0, 100.0], 80.0),
        y_axis_unit=_CELSIUS,
        requested_vertical_range=requested,
        temperature_unit=TemperatureUnit.FAHRENHEIT,
    )

    fahrenheit = _drawing(
        _graph(
            lines=[
                EvaluatedLine(
                    curve=_curve("Temperature", [32.0, 122.0, 212.0], unit=_FAHRENHEIT),
                    inverse=False,
                )
            ],
            rules=[_rule(176.0, unit=_FAHRENHEIT)],
            vertical_range=requested,
        ),
        y_axis_unit=_FAHRENHEIT,
        temperature_unit=TemperatureUnit.FAHRENHEIT,
    )

    assert celsius == fahrenheit


def test_a_mirrored_rule_is_drawn_below_zero() -> None:
    line = EvaluatedLine(curve=_curve("m", [1.0, 2.0, 3.0]), inverse=True)
    rule = EvaluatedRule(
        id="warn",
        attributes=CurveAttributes(title="Warn", unit=_UNIT, color="#ffd000"),
        value=2.0,
        inverse=True,
    )

    drawing = _drawing(_graph(lines=[line], rules=[rule]))

    assert [drawn.value for drawn in drawing.rules] == [-2.0]


def test_a_fixed_range_open_at_the_top_follows_the_data_there() -> None:
    line = EvaluatedLine(curve=_curve("m", [1.0, 2.0, 3.0]), inverse=False)

    drawing = _drawing(
        _graph(
            lines=[line],
            vertical_range=EvaluatedVerticalRange(
                range_kind=VerticalRangeKind.FIXED, lower=0.0, upper=None
            ),
        )
    )

    assert drawing.y_range == (0.0, 3.0)


def test_a_fixed_range_open_at_the_top_keeps_its_bound_without_data() -> None:
    line = EvaluatedLine(curve=_curve("m", [None, None, None]), inverse=False)

    drawing = _drawing(
        _graph(
            lines=[line],
            vertical_range=EvaluatedVerticalRange(
                range_kind=VerticalRangeKind.FIXED, lower=100.0, upper=None
            ),
        )
    )

    assert drawing.y_range == (100.0, 101.0)


def _region(
    *, lower: list[float | None] | None, upper: list[float | None] | None
) -> EvaluatedRegion:
    return EvaluatedRegion(
        id="region-0",
        attributes=CurveAttributes(title="OK", unit=_UNIT, color="#15d1a0"),
        lower=None if lower is None else TimeSeries(time_range=_TIME_RANGE, values=lower),
        upper=None if upper is None else TimeSeries(time_range=_TIME_RANGE, values=upper),
    )


def test_a_line_is_drawn_at_its_values() -> None:
    line = EvaluatedLine(curve=_curve("m", [1.0, None, 3.0]), inverse=False)

    drawing = _drawing(_graph(lines=[line]))

    assert drawing.lines[0].values == [1.0, None, 3.0]


def test_a_mirrored_line_is_drawn_below_zero() -> None:
    line = EvaluatedLine(curve=_curve("m", [1.0, None, 3.0]), inverse=True)

    drawing = _drawing(_graph(lines=[line]))

    assert drawing.lines[0].values == [-1.0, None, -3.0]


def test_a_region_is_drawn_between_its_bounds() -> None:
    line = EvaluatedLine(curve=_curve("m", [0.0, 5.0, 10.0]), inverse=False)

    drawing = _drawing(
        _graph(lines=[line], regions=[_region(lower=[2.0, 2.0, None], upper=[4.0, 4.0, 4.0])])
    )

    assert (drawing.regions[0].lower, drawing.regions[0].upper) == (
        [2.0, 2.0, None],
        [4.0, 4.0, 4.0],
    )


def test_a_region_without_an_upper_bound_reaches_up_to_the_top_of_the_axis() -> None:
    line = EvaluatedLine(curve=_curve("m", [1.0, 2.0, 3.0]), inverse=False)

    drawing = _drawing(_graph(lines=[line], regions=[_region(lower=[2.0, 2.0, 2.0], upper=None)]))

    assert drawing.regions[0].upper == [3.0, 3.0, 3.0]


def test_the_legend_shows_the_value_of_a_rule_as_its_last_value() -> None:
    stack = EvaluatedStack(members=[_curve("m", [1.0, 2.0, 3.0])], inverse=False)

    drawing = _drawing(_graph(stacks=[stack], rules=[_rule(2.5)]))

    assert drawing.legend is not None and drawing.legend.rules[0].cells == [
        "Crit",
        "",
        "",
        "",
        "2.50",
    ]


def test_the_legend_lists_a_region_by_its_title() -> None:
    line = EvaluatedLine(curve=_curve("m", [1.0, 2.0, 3.0]), inverse=False)

    drawing = _drawing(_graph(lines=[line], regions=[_region(lower=None, upper=[2.0] * 3)]))

    assert drawing.legend is not None and drawing.legend.regions[0].cells == [
        "OK",
        "",
        "",
        "",
        "",
    ]


def test_a_fixed_vertical_range_ignores_the_data() -> None:
    line = EvaluatedLine(curve=_curve("m", [1.0, 20.0, 30.0]), inverse=False)

    drawing = _drawing(
        _graph(
            lines=[line],
            vertical_range=EvaluatedVerticalRange(
                range_kind=VerticalRangeKind.FIXED, lower=0.0, upper=10.0
            ),
        )
    )

    assert drawing.y_range == (0.0, 10.0)


def test_a_minimal_vertical_range_widens_to_the_data() -> None:
    line = EvaluatedLine(curve=_curve("m", [1.0, 20.0, 150.0]), inverse=False)

    drawing = _drawing(
        _graph(
            lines=[line],
            vertical_range=EvaluatedVerticalRange(
                range_kind=VerticalRangeKind.MINIMAL, lower=0.0, upper=100.0
            ),
        )
    )

    assert drawing.y_range == (0.0, 150.0)


def test_a_flat_graph_gets_a_vertical_range_of_one_unit() -> None:
    line = EvaluatedLine(curve=_curve("m", [5.0, 5.0, 5.0]), inverse=False)

    drawing = _drawing(_graph(lines=[line]))

    assert drawing.y_range == (5.0, 6.0)


def test_the_vertical_axis_is_labelled_in_the_unit_of_the_graph() -> None:
    line = EvaluatedLine(curve=_curve("m", [1000.0, 2000.0, 3000.0]), inverse=False)

    drawing = _drawing(
        _graph(lines=[line]),
        y_axis_unit=Unit(notation=DecimalNotation("B"), precision=AutoPrecision(2)),
    )

    assert (
        drawing.vertical_axis is not None
        and drawing.vertical_axis.labels
        and all(label.text.endswith("B") for label in drawing.vertical_axis.labels)
    )


def test_a_graph_without_a_unit_leaves_the_labels_of_the_vertical_axis_to_the_renderer() -> None:
    line = EvaluatedLine(curve=_curve("m", [1.0, 2.0, 3.0]), inverse=False)

    drawing = _drawing(_graph(lines=[line]))

    assert drawing.vertical_axis is not None and drawing.vertical_axis.labels is None

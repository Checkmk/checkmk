#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import struct
from zoneinfo import ZoneInfo

import matplotlib
import numpy as np

from cmk.graphing_engine import (
    AutoPrecision,
    CurveAttributes,
    DecimalNotation,
    EvaluatedCurve,
    EvaluatedGraph,
    EvaluatedLine,
    EvaluatedRule,
    EvaluatedStack,
    EvaluatedVerticalRange,
    TimeRange,
    TimeSeries,
    Unit,
    VerticalRangeKind,
)

matplotlib.use("Agg")
from matplotlib.figure import Figure

from cmk.gui.png import compute_png_size_mm
from cmk.gui.png._size import MM_PER_INCH, PngOptions
from cmk.gui.png.renderer._image import (
    _fit_time_axis,
    _graph_scalars,
    _graph_time_caption,
    _mirrored_y_labels,
    _plot_metrics,
    _plot_stack,
    _rules_in_range,
    _vertical_range_bounds,
    _y_axis_limits,
    DPI,
    PngGraph,
    PngTexts,
    render_pngs,
    RenderingFailure,
)
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.web.utils.unit_formatter import DecimalFormatter

_UNIT = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))
_TIME_RANGE = TimeRange(start=0, end=180, step=60)


def _options(*, show_legend: bool) -> PngOptions:
    return PngOptions(
        size=(70.0, 16.0),
        font_size=8.0,
        show_title=True,
        show_legend=show_legend,
        show_vertical_axis=True,
        show_time_axis=True,
        show_graph_time=True,
    )


_OPTIONS = _options(show_legend=True)
_TEXTS = PngTexts(
    minimum="Min",
    maximum="Max",
    average="Average",
    last="Last",
    date_format="%Y-%m-%d",
    caption="for %(date_range)s, resolution: %(resolution)s",
)


def _size_in_px(png: bytes) -> tuple[int, int]:
    width, height = struct.unpack(">II", png[16:24])
    return width, height


def _px(size_mm: tuple[float, float]) -> tuple[int, int]:
    width_mm, height_mm = size_mm
    return int(width_mm / MM_PER_INCH * DPI), int(height_mm / MM_PER_INCH * DPI)


def _curve(title: str, values: list[float | None], *, color: str = "#000000") -> EvaluatedCurve:
    return EvaluatedCurve(
        id=title,
        attributes=CurveAttributes(title=title, unit=_UNIT, color=color),
        value=None,
        time_series=TimeSeries(time_range=_TIME_RANGE, values=values),
    )


def test_second_area_stacks_onto_the_first_not_onto_zero() -> None:
    first = _curve("first", [1.0, 2.0, 3.0])
    second = _curve("second", [10.0, 20.0, 30.0])
    stack = EvaluatedStack(members=[first, second], inverse=False)

    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)
    _plot_stack(ax, stack, [0, 60, 120])

    # Two fill_between calls: one per stacked member, in stacking order.
    assert len(ax.collections) == 2
    second_poly = np.asarray(ax.collections[1].get_paths()[0].vertices)
    # The second member's polygon must reach up to first + second (33 at the last point,
    # since 3.0 + 30.0 = 33.0), not just 30.0 (second alone) as the pre-fix bug produced.
    assert np.isclose(second_poly[:, 1].max(), 33.0)


def test_mirrored_stack_is_drawn_below_zero() -> None:
    member = _curve("inverse-member", [5.0, 5.0])
    stack = EvaluatedStack(members=[member], inverse=True)

    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)
    _plot_stack(ax, stack, [0, 60])

    top_values = np.asarray(ax.collections[0].get_paths()[0].vertices)[:, 1]
    assert top_values.max() <= 0


def test_graph_scalars_use_the_curves_own_values_not_the_stacked_position() -> None:
    first = _curve("first", [1.0, 2.0, 3.0])
    second = _curve("second", [10.0, 20.0, 30.0])
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        time_range=_TIME_RANGE,
        vertical_range=None,
        stacks=[EvaluatedStack(members=[first, second], inverse=False)],
        lines=[],
    )

    scalars = _graph_scalars(graph)

    assert [s.title for s in scalars] == ["first", "second"]
    assert scalars[0].maximum == 3.0
    assert scalars[1].maximum == 30.0


def test_render_png_produces_bytes_for_an_empty_graph() -> None:
    graph = EvaluatedGraph(
        name="g", title="Empty", time_range=_TIME_RANGE, vertical_range=None, stacks=[], lines=[]
    )
    (png_bytes,) = render_pngs(
        [
            PngGraph(
                graph=graph,
                options=_OPTIONS,
                y_axis_unit=None,
                requested_vertical_range=None,
                time_zone=None,
            )
        ],
        _TEXTS,
        TemperatureUnit.CELSIUS,
    )

    assert isinstance(png_bytes, bytes) and png_bytes.startswith(b"\x89PNG")


def test_render_png_with_a_unit_renders_ticks_and_legend_via_the_formatter() -> None:
    curve = _curve("m", [1.0, 2.0, 3.0], color="#123456")
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        time_range=_TIME_RANGE,
        vertical_range=None,
        stacks=[EvaluatedStack(members=[curve], inverse=False)],
        lines=[],
    )
    y_axis_unit = Unit(notation=DecimalNotation("X"), precision=AutoPrecision(2))

    (png_bytes,) = render_pngs(
        [
            PngGraph(
                graph=graph,
                options=_OPTIONS,
                y_axis_unit=y_axis_unit,
                requested_vertical_range=None,
                time_zone=None,
            )
        ],
        _TEXTS,
        TemperatureUnit.CELSIUS,
    )

    assert isinstance(png_bytes, bytes) and png_bytes.startswith(b"\x89PNG")


def test_graph_scalars_are_natural_values_even_when_mirrored() -> None:
    member = _curve("out", [10.0, 20.0, 30.0])
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        time_range=_TIME_RANGE,
        vertical_range=None,
        stacks=[EvaluatedStack(members=[member], inverse=True)],
        lines=[],
    )

    scalars = _graph_scalars(graph)

    assert scalars[0].minimum == 10.0
    assert scalars[0].maximum == 30.0
    assert scalars[0].last == 30.0


def test_mirrored_y_labels_mirrors_positive_text_to_the_negative_side() -> None:
    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.set_ylim(-2000, 2000)
    formatter = DecimalFormatter(symbol="B", precision_kind="auto", digits=2)

    labels = _mirrored_y_labels(ax, formatter, 4.0)

    positive = {label.position: label.text for label in labels if label.position > 0}
    negative = {label.position: label.text for label in labels if label.position < 0}
    assert positive
    for position, text in positive.items():
        assert negative[-position] == text


def test_far_away_rule_is_clipped_and_does_not_stretch_the_axis() -> None:
    member = _curve("m", [1.0, 2.0, 3.0])
    far_away_rule = EvaluatedRule(
        id="crit",
        attributes=CurveAttributes(title="Crit", unit=_UNIT, color="#ff0000"),
        value=100000.0,
        inverse=False,
    )
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        time_range=_TIME_RANGE,
        vertical_range=None,
        stacks=[EvaluatedStack(members=[member], inverse=False)],
        lines=[],
        rules=[far_away_rule],
    )

    lower, upper = _vertical_range_bounds(graph)
    rules = _rules_in_range(graph.rules, lower, upper)
    limits = _y_axis_limits(lower, upper, is_mirrored=False)

    assert rules == []
    assert limits is not None
    assert limits[1] < 100000.0


def test_vertical_range_bounds_use_the_stacked_top_not_each_members_own_max() -> None:
    first = _curve("first", [10.0, 10.0, 10.0])
    second = _curve("second", [20.0, 20.0, 20.0])
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        time_range=_TIME_RANGE,
        vertical_range=None,
        stacks=[EvaluatedStack(members=[first, second], inverse=False)],
        lines=[],
    )

    lower, upper = _vertical_range_bounds(graph)

    assert lower == 0.0
    assert upper == 30.0


def test_y_axis_limits_are_symmetric_for_a_mirrored_graph() -> None:
    assert _y_axis_limits(2.0, 30.0, is_mirrored=True) == (-30.0, 30.0)


def test_the_image_has_the_size_computed_for_it_without_a_legend() -> None:
    curve = _curve("m", [1.0, 2.0, 3.0])
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        time_range=_TIME_RANGE,
        vertical_range=None,
        stacks=[EvaluatedStack(members=[curve], inverse=False)],
        lines=[],
    )
    options = _options(show_legend=False)

    (png_bytes,) = render_pngs(
        [
            PngGraph(
                graph=graph,
                options=options,
                y_axis_unit=_UNIT,
                requested_vertical_range=None,
                time_zone=None,
            )
        ],
        _TEXTS,
        TemperatureUnit.CELSIUS,
    )

    assert isinstance(png_bytes, bytes) and _size_in_px(png_bytes) == _px(
        compute_png_size_mm(graph, options)
    )


def test_the_image_has_the_size_computed_for_it_with_a_legend() -> None:
    curve = _curve("m", [1.0, 2.0, 3.0])
    rule = EvaluatedRule(
        id="crit",
        attributes=CurveAttributes(title="Crit", unit=_UNIT, color="#ff0000"),
        value=2.5,
        inverse=False,
    )
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        time_range=_TIME_RANGE,
        vertical_range=None,
        stacks=[EvaluatedStack(members=[curve], inverse=False)],
        lines=[],
        rules=[rule],
    )
    options = _options(show_legend=True)

    (png_bytes,) = render_pngs(
        [
            PngGraph(
                graph=graph,
                options=options,
                y_axis_unit=_UNIT,
                requested_vertical_range=None,
                time_zone=None,
            )
        ],
        _TEXTS,
        TemperatureUnit.CELSIUS,
    )

    assert isinstance(png_bytes, bytes) and _size_in_px(png_bytes) == _px(
        compute_png_size_mm(graph, options)
    )


def test_plot_metrics_spans_the_full_time_range_despite_a_long_leading_gap() -> None:
    """Regression test for CMK-38506."""
    time_range = TimeRange(start=0, end=720, step=60)
    curve = EvaluatedCurve(
        id="m",
        attributes=CurveAttributes(title="m", unit=_UNIT, color="#000000"),
        value=None,
        time_series=TimeSeries(time_range=time_range, values=[None] * 10 + [5.0, 6.0]),
    )
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        time_range=time_range,
        vertical_range=None,
        stacks=[EvaluatedStack(members=[curve], inverse=False)],
        lines=[],
    )

    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)
    _plot_metrics(ax, graph)

    assert ax.get_xlim() == (time_range.start, time_range.end)


def test_plot_metrics_spans_the_full_time_range_for_an_entirely_empty_curve() -> None:
    curve = _curve("m", [None, None, None])
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        time_range=_TIME_RANGE,
        vertical_range=None,
        stacks=[EvaluatedStack(members=[curve], inverse=False)],
        lines=[],
    )

    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)
    _plot_metrics(ax, graph)

    assert ax.get_xlim() == (_TIME_RANGE.start, _TIME_RANGE.end)


def test_plot_metrics_spans_the_time_range_of_a_graph_without_curves() -> None:
    graph = EvaluatedGraph(
        name="g", title="Empty", time_range=_TIME_RANGE, vertical_range=None, stacks=[], lines=[]
    )

    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)
    _plot_metrics(ax, graph)

    assert ax.get_xlim() == (_TIME_RANGE.start, _TIME_RANGE.end)


def test_time_axis_of_a_multi_day_graph_is_labelled_with_weekday_and_time() -> None:
    two_days = TimeRange(start=1668426600, end=1668426600 + 2 * 86400, step=3600)
    curve = EvaluatedCurve(
        id="m",
        attributes=CurveAttributes(title="m", unit=_UNIT, color="#000000"),
        value=None,
        time_series=TimeSeries(time_range=two_days, values=[1.0] * 48),
    )
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        time_range=two_days,
        vertical_range=None,
        stacks=[EvaluatedStack(members=[curve], inverse=False)],
        lines=[],
    )
    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)
    _plot_metrics(ax, graph)

    _fit_time_axis(ax, _OPTIONS, None)

    labels = [label.get_text() for label in ax.get_xticklabels() if label.get_text()]
    assert len(labels) > 2
    assert all(re.fullmatch(r"\w+ \d{2}:\d{2}", label) for label in labels)


def test_values_are_drawn_at_their_bucket_end_like_the_vue_graph() -> None:
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        time_range=_TIME_RANGE,
        vertical_range=None,
        stacks=[],
        lines=[EvaluatedLine(curve=_curve("m", [1.0, 2.0, 3.0]), inverse=False)],
    )
    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)

    _plot_metrics(ax, graph)

    (line,) = ax.get_lines()
    assert np.asarray(line.get_xdata()).tolist() == [60, 120, 180]


def _hourly_graph(time_range: TimeRange) -> EvaluatedGraph:
    curve = EvaluatedCurve(
        id="m",
        attributes=CurveAttributes(title="m", unit=_UNIT, color="#000000"),
        value=None,
        time_series=TimeSeries(
            time_range=time_range,
            values=[1.0] * ((time_range.end - time_range.start) // time_range.step),
        ),
    )
    return EvaluatedGraph(
        name="g",
        title="Graph",
        time_range=time_range,
        vertical_range=None,
        stacks=[EvaluatedStack(members=[curve], inverse=False)],
        lines=[],
    )


def test_time_axis_is_labelled_in_the_given_time_zone() -> None:
    # 2026-09-28 10:00 to 14:00 UTC, i.e. 12:00 to 16:00 in Berlin (CEST, UTC+2).
    graph = _hourly_graph(TimeRange(start=1790589600, end=1790604000, step=600))

    def labels(tz: ZoneInfo) -> list[str]:
        fig = Figure()
        ax = fig.add_subplot(1, 1, 1)
        _plot_metrics(ax, graph)
        _fit_time_axis(ax, _OPTIONS, tz)
        return [label.get_text() for label in ax.get_xticklabels() if label.get_text()]

    utc_labels = labels(ZoneInfo("UTC"))

    assert utc_labels
    assert labels(ZoneInfo("Europe/Berlin")) == [
        f"{int(label[:2]) + 2:02d}{label[2:]}" for label in utc_labels
    ]


def test_graph_time_caption_dates_the_range_in_the_given_time_zone() -> None:
    # 2026-09-28 23:00 UTC is already 2026-09-29 in Berlin.
    time_range = TimeRange(start=1790636400, end=1790640000, step=60)

    assert "2026-09-28" in _graph_time_caption(time_range, _TEXTS, ZoneInfo("UTC"))
    assert "2026-09-29" in _graph_time_caption(time_range, _TEXTS, ZoneInfo("Europe/Berlin"))


def _temperature_graph(unit: Unit, values: list[float | None], warning: float) -> EvaluatedGraph:
    return EvaluatedGraph(
        name="g",
        title="Temperature",
        time_range=_TIME_RANGE,
        vertical_range=None,
        stacks=[],
        lines=[
            EvaluatedLine(
                curve=EvaluatedCurve(
                    id="temp",
                    attributes=CurveAttributes(title="Temperature", unit=unit, color="#123456"),
                    value=None,
                    time_series=TimeSeries(time_range=_TIME_RANGE, values=values),
                ),
                inverse=False,
            )
        ],
        rules=[
            EvaluatedRule(
                id="warn",
                attributes=CurveAttributes(title="Warning", unit=unit, color="#ffd000"),
                value=warning,
                inverse=False,
            )
        ],
    )


def test_a_celsius_graph_renders_like_its_fahrenheit_twin_for_a_fahrenheit_user() -> None:
    celsius = Unit(notation=DecimalNotation("°C"), precision=AutoPrecision(2))
    fahrenheit = Unit(notation=DecimalNotation("°F"), precision=AutoPrecision(2))

    (celsius_png,) = render_pngs(
        [
            PngGraph(
                graph=_temperature_graph(celsius, [0.0, 50.0, 100.0], 80.0),
                options=_OPTIONS,
                y_axis_unit=celsius,
                requested_vertical_range=None,
                time_zone=None,
            )
        ],
        _TEXTS,
        TemperatureUnit.FAHRENHEIT,
    )
    (fahrenheit_png,) = render_pngs(
        [
            PngGraph(
                graph=_temperature_graph(fahrenheit, [32.0, 122.0, 212.0], 176.0),
                options=_OPTIONS,
                y_axis_unit=fahrenheit,
                requested_vertical_range=None,
                time_zone=None,
            )
        ],
        _TEXTS,
        TemperatureUnit.FAHRENHEIT,
    )

    assert isinstance(celsius_png, bytes) and celsius_png == fahrenheit_png


def test_each_graph_of_a_batch_gets_its_own_image_in_order() -> None:
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        time_range=_TIME_RANGE,
        vertical_range=None,
        stacks=[EvaluatedStack(members=[_curve("m", [1.0, 2.0, 3.0])], inverse=False)],
        lines=[],
    )
    with_legend = _options(show_legend=True)
    without_legend = _options(show_legend=False)

    pngs = render_pngs(
        [
            PngGraph(
                graph=graph,
                options=with_legend,
                y_axis_unit=None,
                requested_vertical_range=None,
                time_zone=None,
            ),
            PngGraph(
                graph=graph,
                options=without_legend,
                y_axis_unit=None,
                requested_vertical_range=None,
                time_zone=None,
            ),
        ],
        _TEXTS,
        TemperatureUnit.CELSIUS,
    )

    assert [_size_in_px(png) for png in pngs if isinstance(png, bytes)] == [
        _px(compute_png_size_mm(graph, with_legend)),
        _px(compute_png_size_mm(graph, without_legend)),
    ]


def test_a_requested_vertical_range_is_taken_in_the_users_unit() -> None:
    celsius = Unit(notation=DecimalNotation("°C"), precision=AutoPrecision(2))
    fahrenheit = Unit(notation=DecimalNotation("°F"), precision=AutoPrecision(2))
    requested = EvaluatedVerticalRange(range_kind=VerticalRangeKind.FIXED, lower=50.0, upper=100.0)
    twin = _temperature_graph(fahrenheit, [32.0, 122.0, 212.0], 176.0)

    (celsius_png,) = render_pngs(
        [
            PngGraph(
                graph=_temperature_graph(celsius, [0.0, 50.0, 100.0], 80.0),
                options=_OPTIONS,
                y_axis_unit=celsius,
                requested_vertical_range=requested,
                time_zone=None,
            )
        ],
        _TEXTS,
        TemperatureUnit.FAHRENHEIT,
    )
    (fahrenheit_png,) = render_pngs(
        [
            PngGraph(
                graph=EvaluatedGraph(
                    name=twin.name,
                    title=twin.title,
                    time_range=twin.time_range,
                    vertical_range=requested,
                    stacks=twin.stacks,
                    lines=twin.lines,
                    rules=twin.rules,
                    regions=twin.regions,
                ),
                options=_OPTIONS,
                y_axis_unit=fahrenheit,
                requested_vertical_range=None,
                time_zone=None,
            )
        ],
        _TEXTS,
        TemperatureUnit.FAHRENHEIT,
    )

    assert isinstance(celsius_png, bytes) and celsius_png == fahrenheit_png


def test_a_graph_that_fails_to_render_leaves_the_others_their_images() -> None:
    def png_graph(values: list[float | None]) -> PngGraph:
        return PngGraph(
            graph=EvaluatedGraph(
                name="g",
                title="Graph",
                time_range=_TIME_RANGE,
                vertical_range=None,
                stacks=[],
                lines=[EvaluatedLine(curve=_curve("m", values), inverse=False)],
            ),
            options=_OPTIONS,
            y_axis_unit=None,
            requested_vertical_range=None,
            time_zone=None,
        )

    results = render_pngs(
        [png_graph([1.0, 2.0, 3.0, 4.0]), png_graph([1.0, 2.0, 3.0])],
        _TEXTS,
        TemperatureUnit.CELSIUS,
    )

    assert [type(result) for result in results] == [RenderingFailure, bytes]

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
    TimeRange,
    TimeSeries,
    Unit,
)

matplotlib.use("Agg")
from matplotlib.figure import Figure

from cmk.gui.graphing._graph_display_config import GraphDisplayConfigImage
from cmk.gui.graphing._graph_png import (
    _all_curves_with_sign,
    _derive_y_axis,
    _graph_scalars,
    _mirrored_y_labels,
    _notation_formatter,
    _plot_stack,
    _rules_in_range,
    _stack_extents,
    _values,
    _vertical_range_bounds,
    _y_axis_limits,
    compute_png_size_mm,
    render_png,
    render_png_ex,
    render_png_graphs,
)
from cmk.shared_typing.cmk_time_series_graph import Precision, UnitFormat, YAxis

_UNIT = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))
_TIME_RANGE = TimeRange(start=0, end=180, step=60)


def _curve(title: str, values: list[float | None], *, color: str = "#000000") -> EvaluatedCurve:
    return EvaluatedCurve(
        id=title,
        attributes=CurveAttributes(title=title, unit=_UNIT, color=color),
        value=None,
        time_series=TimeSeries(time_range=_TIME_RANGE, values=values),
    )


def test_second_area_stacks_onto_the_first_not_onto_zero() -> None:
    """Regression test for the bug the matplotlib PNG rewrite introduced: a second stacked
    curve must pile onto the first curve's top, not reset to a zero baseline."""
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
    """Legend min/max/avg/last must reflect each curve's own series, not its cumulative
    position within the stack (matching the legacy artwork behaviour)."""
    first = _curve("first", [1.0, 2.0, 3.0])
    second = _curve("second", [10.0, 20.0, 30.0])
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        vertical_range=None,
        stacks=[EvaluatedStack(members=[first, second], inverse=False)],
        lines=[],
    )

    scalars = _graph_scalars(graph)

    assert [s.title for s in scalars] == ["first", "second"]
    assert scalars[0].maximum == 3.0
    assert scalars[1].maximum == 30.0


def test_all_curves_with_sign_lists_stacks_then_lines() -> None:
    stacked = _curve("stacked", [1.0])
    lined = _curve("lined", [2.0])
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        vertical_range=None,
        stacks=[EvaluatedStack(members=[stacked], inverse=False)],
        lines=[EvaluatedLine(curve=lined, inverse=True)],
    )

    result = _all_curves_with_sign(graph)

    assert result == [(stacked, 1.0), (lined, -1.0)]


def test_render_png_produces_bytes_for_an_empty_graph() -> None:
    graph = EvaluatedGraph(name="g", title="Empty", vertical_range=None, stacks=[], lines=[])
    png_bytes = render_png(graph, GraphDisplayConfigImage())

    assert png_bytes.startswith(b"\x89PNG")


def test_notation_formatter_is_none_without_a_y_axis() -> None:
    assert _notation_formatter(None) is None


def test_notation_formatter_never_converts_temperature_values() -> None:
    """The engine fetch does not (yet) convert values for the user's temperature preference, so
    the PNG renderer must never apply a real conversion formula to a celsius/fahrenheit unit -
    doing so would mislabel the still-unconverted plotted values."""
    y_axis = YAxis(
        title="",
        unit=UnitFormat(
            notation="decimal", symbol="°C", precision=Precision(type="auto", digits=2)
        ),
    )
    formatter = _notation_formatter(y_axis)
    assert formatter is not None
    assert formatter.symbol == "°C"
    assert formatter.render(10) == "10 °C"


def test_render_png_ex_with_a_unit_renders_ticks_and_legend_via_the_formatter() -> None:
    """End-to-end smoke test: a graph with a Y-axis unit must render without error through the
    render_y_labels()/formatter.render() wiring, not just the plain-numeric fallback path."""
    curve = _curve("m", [1.0, 2.0, 3.0], color="#123456")
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        vertical_range=None,
        stacks=[EvaluatedStack(members=[curve], inverse=False)],
        lines=[],
    )
    y_axis = YAxis(
        title="",
        unit=UnitFormat(notation="decimal", symbol="X", precision=Precision(type="auto", digits=2)),
    )

    png_bytes, _width_mm, _height_mm = render_png_ex(graph, GraphDisplayConfigImage(), y_axis)

    assert png_bytes.startswith(b"\x89PNG")


def test_graph_scalars_are_natural_values_even_when_mirrored() -> None:
    """Legend min/max/avg/last must reflect the curve's true (positive) value, not the
    display-mirroring sign - Min/Max must not swap or go negative for an inverse curve."""
    member = _curve("out", [10.0, 20.0, 30.0])
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        vertical_range=None,
        stacks=[EvaluatedStack(members=[member], inverse=True)],
        lines=[],
    )

    scalars = _graph_scalars(graph)

    assert scalars[0].minimum == 10.0
    assert scalars[0].maximum == 30.0
    assert scalars[0].last == 30.0


def test_mirrored_y_labels_mirrors_positive_text_to_the_negative_side() -> None:
    """A mirrored graph's negative half must show the same (positive-looking) label text as its
    mirror image above zero - mirroring below zero is a display choice, not a sign change."""
    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.set_ylim(-2000, 2000)
    y_axis = YAxis(
        title="",
        unit=UnitFormat(notation="decimal", symbol="B", precision=Precision(type="auto", digits=2)),
    )
    formatter = _notation_formatter(y_axis)
    assert formatter is not None

    labels = _mirrored_y_labels(ax, formatter, 4.0)

    positive = {label.position: label.text for label in labels if label.position > 0}
    negative = {label.position: label.text for label in labels if label.position < 0}
    assert positive
    for position, text in positive.items():
        assert negative[-position] == text


def test_far_away_rule_is_clipped_and_does_not_stretch_the_axis() -> None:
    """A rule far outside the curve data's range must not be drawn on the plot, and the computed
    ylim must stay anchored to the data - matching Vue's computeYDomain, which never factors rule
    values into the axis range."""
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
    """A stack's drawn top is the cumulative sum other members pile onto, so the Y-axis bounds
    must follow that stacked geometry (matching _artwork._compute_min_max, which runs over the
    layouted/stacked points) - not each member's own unstacked min/max (_CurveScalars, which is
    legend-only). Regression test for a bug where a stack of members maxing 10 and 20 drew up to
    30 but the axis was clipped at 20, and the area's zero baseline was lost entirely."""
    first = _curve("first", [10.0, 10.0, 10.0])
    second = _curve("second", [20.0, 20.0, 20.0])
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        vertical_range=None,
        stacks=[EvaluatedStack(members=[first, second], inverse=False)],
        lines=[],
    )

    lower, upper = _vertical_range_bounds(graph)

    assert lower == 0.0
    assert upper == 30.0


def test_y_axis_limits_are_symmetric_for_a_mirrored_graph() -> None:
    assert _y_axis_limits(2.0, 30.0, is_mirrored=True) == (-30.0, 30.0)


def test_derive_y_axis_reads_unit_from_the_first_curve() -> None:
    curve = _curve("m", [1.0])
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        vertical_range=None,
        stacks=[EvaluatedStack(members=[curve], inverse=False)],
        lines=[],
    )

    y_axis = _derive_y_axis(graph)

    assert y_axis is not None
    assert y_axis.unit.notation == "decimal"
    assert y_axis.unit.precision.digits == 2


def test_derive_y_axis_is_none_for_a_graph_with_no_curves() -> None:
    graph = EvaluatedGraph(name="g", title="Empty", vertical_range=None, stacks=[], lines=[])

    assert _derive_y_axis(graph) is None


def test_render_png_ex_self_derives_the_y_axis_when_none_is_passed() -> None:
    """render_png/render_png_ex now derive their own Y-axis from the evaluated graph by default
    (mirroring render_png_graphs), so callers no longer need to compute and pass
    derive_y_axis(graph) (the pre-evaluation Graph's axis) themselves."""
    curve = _curve("m", [1.0, 2.0, 3.0])
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        vertical_range=None,
        stacks=[EvaluatedStack(members=[curve], inverse=False)],
        lines=[],
    )

    default_bytes, _width_mm, _height_mm = render_png_ex(graph, GraphDisplayConfigImage())
    explicit_bytes, _width_mm, _height_mm = render_png_ex(
        graph, GraphDisplayConfigImage(), _derive_y_axis(graph)
    )

    assert default_bytes == explicit_bytes


def test_compute_png_size_mm_matches_render_png_ex_without_a_legend() -> None:
    curve = _curve("m", [1.0, 2.0, 3.0])
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        vertical_range=None,
        stacks=[EvaluatedStack(members=[curve], inverse=False)],
        lines=[],
    )
    config = GraphDisplayConfigImage(show_legend=False)

    _png_bytes, width_mm, height_mm = render_png_ex(graph, config)

    assert compute_png_size_mm(graph, config) == (width_mm, height_mm)


def test_compute_png_size_mm_matches_render_png_ex_with_a_legend() -> None:
    """compute_png_size_mm() must reproduce render_png_ex()'s own legend-table height
    calculation (based on scalar/rule counts) without actually rendering, so callers can plan
    layout/pagination without paying for a matplotlib render per graph."""
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
        vertical_range=None,
        stacks=[EvaluatedStack(members=[curve], inverse=False)],
        lines=[],
        rules=[rule],
    )
    config = GraphDisplayConfigImage(show_legend=True)

    _png_bytes, width_mm, height_mm = render_png_ex(graph, config)

    assert compute_png_size_mm(graph, config) == (width_mm, height_mm)


def test_render_png_graphs_formats_ticks_via_the_unit_formatter() -> None:
    """render_png_graphs (the multi-graph combined path) must derive and apply its own
    per-graph Y-axis unit, not render with unformatted (raw) ticks."""
    curve = _curve("m", [1.0, 2.0, 3.0])
    graph = EvaluatedGraph(
        name="g",
        title="Graph",
        vertical_range=None,
        stacks=[EvaluatedStack(members=[curve], inverse=False)],
        lines=[],
    )

    png_bytes = render_png_graphs([graph], GraphDisplayConfigImage())

    assert png_bytes.startswith(b"\x89PNG")


def test_values_pads_a_shorter_curve_with_nan_to_match_length() -> None:
    """A Sum/Product curve whose own RRD fetch came up shorter than another operand's (see
    _curves_length's docstring) must be padded with NaN out to the shared length, not raise or
    silently drop the mismatch."""
    curve = _curve("m", [1.0, 2.0])

    padded = _values(curve, length=4)

    assert padded.tolist()[:2] == [1.0, 2.0]
    assert np.isnan(padded[2:]).all()


def test_stack_extents_pads_a_shorter_member_to_the_longest_curve() -> None:
    """Mirrors _curves_length's rationale: two stack members can legitimately differ in length,
    so _stack_extents must pad the shorter one instead of crashing on the numpy broadcast."""
    longer = _curve("longer", [1.0, 1.0, 1.0])
    shorter = _curve("shorter", [10.0, 20.0])
    stack = EvaluatedStack(members=[longer, shorter], inverse=False)

    extents = _stack_extents(stack, timestamps=[0, 60, 120])

    _bottom, longer_top, longer_has_value = extents[0]
    _bottom, _top, shorter_has_value = extents[1]
    assert longer_has_value.tolist() == [True, True, True]
    assert shorter_has_value.tolist() == [True, True, False]
    # The padded (missing) position must not contribute to the running stack sum.
    assert longer_top[2] == 1.0

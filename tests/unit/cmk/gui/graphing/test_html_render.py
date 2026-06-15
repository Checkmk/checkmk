#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.gui.graphing import MKGraphWidgetTooSmallError
from cmk.gui.graphing._artwork import (
    ActualTimeRange,
    Axis,
    Curve,
    CurveAnnotations,
    GraphArtwork,
    GraphArtworkAnnotations,
    LayoutedCurve,
    LayoutedCurveArea,
    LayoutedCurveLine,
    LayoutedCurveStack,
    RequestedTimeRange,
    Scalars,
)
from cmk.gui.graphing._graph_display_config import GraphDisplayConfigHTML
from cmk.gui.graphing._html_render import (
    _legend_height_ex,
    _MIN_LEGEND_HEIGHT_EX,
    _MIN_WIDGET_HEIGHT_EX,
    _order_graph_curves_for_legend_and_mouse_hover,
    _show_graph_legend,
    ExpandableLegendAppearance,
)
from cmk.gui.utils.output_funnel import output_funnel


def _curve_annotation() -> CurveAnnotations:
    return CurveAnnotations(
        scalars=Scalars(
            pin=(None, ""),
            last=(None, ""),
            max=(None, ""),
            min=(None, ""),
            average=(None, ""),
        ),
        attributes={},
    )


def test__order_graph_curves_for_legend_and_mouse_hover_curves() -> None:
    rendered_value = (123.456, "123.456")
    curves = [
        Curve(
            line_type="line",
            color="",
            title="1",
            rendered_value=rendered_value,
        ),
        Curve(
            line_type="ref",
            color="",
            title="2",
            rendered_value=rendered_value,
        ),
        Curve(
            line_type="-area",
            color="",
            title="3",
            rendered_value=rendered_value,
        ),
        Curve(
            line_type="stack",
            color="",
            title="4",
            rendered_value=rendered_value,
        ),
        Curve(
            line_type="area",
            color="",
            title="5",
            rendered_value=rendered_value,
        ),
        Curve(
            line_type="-stack",
            color="",
            title="6",
            rendered_value=rendered_value,
        ),
        Curve(
            line_type="stack",
            color="",
            title="7",
            rendered_value=rendered_value,
        ),
    ]
    assert [
        c
        for c, _ in _order_graph_curves_for_legend_and_mouse_hover(
            curves,
            [_curve_annotation() for _ in range(len(curves))],
        )
    ] == [
        Curve(
            color="",
            line_type="line",
            rendered_value=rendered_value,
            title="1",
        ),
        Curve(
            color="",
            line_type="stack",
            rendered_value=rendered_value,
            title="7",
        ),
        Curve(
            color="",
            line_type="area",
            rendered_value=rendered_value,
            title="5",
        ),
        Curve(
            color="",
            line_type="stack",
            rendered_value=rendered_value,
            title="4",
        ),
        Curve(
            color="",
            line_type="-area",
            rendered_value=rendered_value,
            title="3",
        ),
        Curve(
            color="",
            line_type="-stack",
            rendered_value=rendered_value,
            title="6",
        ),
        Curve(
            color="",
            line_type="ref",
            rendered_value=rendered_value,
            title="2",
        ),
    ]


@pytest.mark.parametrize(
    "curves, result",
    [
        pytest.param(
            [
                LayoutedCurveStack(
                    line_type="stack",
                    color="",
                    title="1",
                    points=[],
                ),
                LayoutedCurveStack(
                    line_type="stack",
                    color="",
                    title="2",
                    points=[],
                ),
                LayoutedCurveLine(
                    line_type="line",
                    color="",
                    title="3",
                    points=[],
                ),
            ],
            [
                LayoutedCurveLine(
                    line_type="line",
                    color="",
                    title="3",
                    points=[],
                ),
                LayoutedCurveStack(
                    line_type="stack",
                    color="",
                    title="2",
                    points=[],
                ),
                LayoutedCurveStack(
                    line_type="stack",
                    color="",
                    title="1",
                    points=[],
                ),
            ],
            id="stack-and-line",
        ),
        pytest.param(
            [
                LayoutedCurveStack(
                    line_type="-stack",
                    color="",
                    title="1",
                    points=[],
                ),
                LayoutedCurveArea(
                    line_type="-area",
                    color="",
                    title="2",
                    points=[],
                ),
                LayoutedCurveLine(
                    line_type="-line",
                    color="",
                    title="3",
                    points=[],
                ),
                LayoutedCurveStack(
                    line_type="stack",
                    color="",
                    title="4",
                    points=[],
                ),
                LayoutedCurveArea(
                    line_type="area",
                    color="",
                    title="5",
                    points=[],
                ),
                LayoutedCurveLine(
                    line_type="line",
                    color="",
                    title="6",
                    points=[],
                ),
            ],
            [
                LayoutedCurveLine(
                    line_type="line",
                    color="",
                    title="6",
                    points=[],
                ),
                LayoutedCurveArea(
                    line_type="area",
                    color="",
                    title="5",
                    points=[],
                ),
                LayoutedCurveStack(
                    line_type="stack",
                    color="",
                    title="4",
                    points=[],
                ),
                LayoutedCurveStack(
                    line_type="-stack",
                    color="",
                    title="1",
                    points=[],
                ),
                LayoutedCurveArea(
                    line_type="-area",
                    color="",
                    title="2",
                    points=[],
                ),
                LayoutedCurveLine(
                    line_type="-line",
                    color="",
                    title="3",
                    points=[],
                ),
            ],
            id="lower-and-upper",
        ),
    ],
)
def test__order_graph_curves_for_legend_and_mouse_hover_layouted_curves(
    curves: Sequence[LayoutedCurve], result: Sequence[LayoutedCurve]
) -> None:
    assert [
        c
        for c, _ in _order_graph_curves_for_legend_and_mouse_hover(
            curves,
            [_curve_annotation() for _ in range(len(curves))],
        )
    ] == result


def _empty_artwork() -> GraphArtwork:
    return GraphArtwork(
        curves=[],
        horizontal_rules=[],
        y_axis=Axis(lower=0.0, upper=1.0, labels=[]),
        x_axis=Axis(lower=0.0, upper=1.0, labels=[]),
        mark_requested_end_time=False,
        actual_time=ActualTimeRange(start=0, end=3600, step=60),
        requested_time=RequestedTimeRange(start=0, end=3600),
        requested_y_range=None,
        pin_time=None,
    )


def _render_legend(display_config: GraphDisplayConfigHTML) -> str:
    with output_funnel.plugged():
        _show_graph_legend(
            None,
            _empty_artwork(),
            GraphArtworkAnnotations(x_axis_title="", curves=[]),
            display_config,
            ExpandableLegendAppearance.POP_UP,
            size_x=40.0,
        )
        return output_funnel.drain()


def test__show_graph_legend_omits_inline_max_height_when_unset(request_context: None) -> None:
    # Dashboard graph widgets leave legend_max_height_px unset (CMK-35215) so the browser
    # sizes the scrollable legend via CSS instead of an inaccurate server-side pixel estimate.
    rendered = _render_legend(GraphDisplayConfigHTML())

    assert 'class="legend_container"' in rendered
    assert "max-height" not in rendered
    assert "overflow-y" not in rendered


def test__show_graph_legend_keeps_inline_max_height_when_set(request_context: None) -> None:
    rendered = _render_legend(GraphDisplayConfigHTML(legend_max_height_px=120))

    assert "max-height: 120px" in rendered
    assert "overflow-y: auto" in rendered


@pytest.mark.parametrize("usable_height_ex", [11.0, 15.0, 16.0])
def test__legend_height_ex_raises_when_widget_too_small(usable_height_ex: float) -> None:
    # The widget must fit the graph floor plus a useful legend, else the caller surfaces
    # the "increase height or disable legend" error.
    with pytest.raises(MKGraphWidgetTooSmallError):
        _legend_height_ex(usable_height_ex, curve_count=10, horizontal_rule_count=0)


def test__legend_height_ex_enforces_minimum_when_legend_scrolls() -> None:
    # Many curves on a near-minimum widget: the legend is clipped and would collapse, so
    # it is kept at the useful minimum while the graph still keeps its floor.
    height = 17.0
    legend = _legend_height_ex(height, curve_count=20, horizontal_rule_count=0)
    assert legend == _MIN_LEGEND_HEIGHT_EX
    assert height - legend >= _MIN_WIDGET_HEIGHT_EX


def test__legend_height_ex_uses_estimate_when_it_fits() -> None:
    # Few curves: reserve only what the legend needs, without forcing the minimum or
    # wasting graph space.
    assert _legend_height_ex(60.0, curve_count=1, horizontal_rule_count=0) == int(3.0 + 1.5)


def test__legend_height_ex_never_exceeds_a_third_or_the_graph() -> None:
    height = 60.0
    legend = _legend_height_ex(height, curve_count=50, horizontal_rule_count=0)
    assert legend <= height // 3
    assert legend < height - legend  # legend never larger than the graph

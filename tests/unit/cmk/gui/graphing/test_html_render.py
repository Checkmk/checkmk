#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.gui.graphing._artwork import (
    Curve,
    CurveAnnotations,
    LayoutedCurve,
    LayoutedCurveArea,
    LayoutedCurveLine,
    LayoutedCurveStack,
    Scalars,
)
from cmk.gui.graphing._html_render import _order_graph_curves_for_legend_and_mouse_hover


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

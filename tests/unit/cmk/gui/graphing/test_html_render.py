#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.gui.config import Config
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
from cmk.gui.graphing._graph_specification import GraphEnvironment
from cmk.gui.graphing._html_render import (
    _order_graph_curves_for_legend_and_mouse_hover,
    _show_graph_legend,
    ExpandableLegendAppearance,
    host_service_graph_popup_cmk,
)
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.livestatus_client.testing import MockLiveStatusConnection
from cmk.utils.servicename import ServiceName


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


# The engine resolves the metric names during the render with a single services query; the legacy
# renderer (render_graphs_html) would instead fetch through fetch_graph_row and emit a div.graph.
_POPUP_SERVICE_ROW = {
    "host_name": "h",
    "description": "svc",
    "perf_data": "x=5",
    "metrics": ["x"],
    "check_command": "check_mk-foo",
}
_POPUP_ENGINE_QUERY = (
    "GET services\nColumns: host_name description perf_data metrics check_command\n"
    "Filter: host_name = h\nFilter: description = svc\nAnd: 2\n"
)


def _graph_environment() -> GraphEnvironment:
    # The popup reads only `debug` off the environment; the engine plugins provide the rest.
    return GraphEnvironment(
        registered_metrics={},
        registered_graphs={},
        user_permissions=UserPermissions({}, {}, {}, []),
        temperature_unit=TemperatureUnit.CELSIUS,
        backend_time_series_fetcher=None,
    )


def _render_popup(mock_livestatus: MockLiveStatusConnection) -> str:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table("services", [_POPUP_SERVICE_ROW])
    mock_livestatus.expect_query(_POPUP_ENGINE_QUERY)
    with mock_livestatus(), output_funnel.plugged():
        host_service_graph_popup_cmk(
            None,
            HostName("h"),
            ServiceName("svc"),
            _graph_environment(),
            graph_timeranges=[],
        )
        return output_funnel.drain()


def test_host_service_graph_popup_renders_the_new_engine_component(
    load_config: Config, mock_livestatus: MockLiveStatusConnection
) -> None:
    output = _render_popup(mock_livestatus)

    # The hover preview renders the service graph through the engine's Vue component ...
    assert "cmk-graph-group" in output
    # ... on the hover graph surface (the wrapper carries the background the component omits) ...
    assert 'class="cmk_graph_hover"' in output
    # ... at the compact legacy popup size (30x10 ex * _HTML_SIZE_PER_EX = 330x110 px), not the
    # group's 800px in-view default.
    assert "figure_width" in output
    assert "330" in output
    assert "figure_height" in output
    assert "110" in output


def test_host_service_graph_popup_does_not_call_the_legacy_renderer(
    load_config: Config, mock_livestatus: MockLiveStatusConnection
) -> None:
    # The strict livestatus mock expects only the engine's metric-name query. The legacy
    # render_graphs_html path would issue an extra fetch_graph_row query (which would fail the
    # strict mock) and emit a div.graph container, so its absence proves it is no longer used.
    output = _render_popup(mock_livestatus)

    assert 'class="graph"' not in output
    assert "graph_ajax" not in output

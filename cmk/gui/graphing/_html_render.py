#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
import traceback
from collections.abc import Callable, Generator, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import auto, Enum
from typing import assert_never, Literal, override
from uuid import uuid4

from pydantic import BaseModel, field_validator, SerializeAsAny

from livestatus import MKLivestatusNotFoundError

import cmk.utils.render
from cmk import trace
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.ccc.version import edition
from cmk.gui.color import render_color_icon
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request, request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import (
    load_user_file,
    save_user_file,
    user,
    UserGraphTimeRangeFileName,
)
from cmk.gui.pages import AjaxPage, Page, PageContext, PageResult
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import GraphTimerange, IconNames, SizePT, StaticIcon
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.popups import MethodAjax
from cmk.gui.utils.rendering import text_with_links_to_user_translated_html
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.gui.valuespec import Timerange, TimerangeValue
from cmk.utils import paths
from cmk.utils.jsontype import JsonSerializable
from cmk.utils.paths import profile_dir
from cmk.utils.servicename import ServiceName

from ._artwork import (
    compute_curves_at_timestamp,
    compute_graph_artwork,
    Curve,
    CurveAnnotations,
    get_step_label,
    GraphArtwork,
    GraphArtworkAnnotations,
    GraphArtworkOrErrors,
    LayoutedCurve,
    Scalars,
)
from ._fetch_time_series import fetch_augmented_time_series
from ._from_api import metrics_from_api, RegisteredMetric
from ._graph_display_config import (
    GraphDisplayConfigHTML,
    GraphRenderOptions,
)
from ._graph_metric_expressions import GraphConsolidationFunction, GraphMetricExpression
from ._graph_specification import (
    AdditionalGraphHTML,
    GraphEnvironment,
    GraphRecipe,
    GraphRecipeWithOverrides,
    GraphSpecification,
    GraphTimeRange,
    parse_graph_specification,
)
from ._graph_templates import (
    get_template_graph_specification,
)
from ._graph_title import iter_graph_title_elements
from ._metric_backend_registry import (
    FetchTimeSeries,
    metric_backend_registry,
)
from ._unit import get_temperature_unit, user_specific_unit
from ._utils import (
    MKGraphRecipeNotFoundError,
    MKGraphWidgetTooSmallError,
)

tracer = trace.get_tracer()

RenderOutput = HTML | str


class ExpandableLegendAppearance(Enum):
    POP_UP = auto()
    FOLDABLE = auto()


class GraphInteractionState(BaseModel, frozen=True):
    """All frontend-mutable graph state; round-tripped on every AJAX call.

    The browser sets graph_id after DOM insertion; all other fields are updated
    by user interactions (drag, zoom, resize, legend column click).
    """

    graph_id: str = ""
    consolidation_function: GraphConsolidationFunction | None = None
    time_start: int
    time_end: int
    # Forecast graphs represent step as str (colon-separated "[step length]:[rrd point count]")
    step: int | str
    value_min: float | None = None
    value_max: float | None = None
    size_x: float
    size_y: float


# The ajax context will be passed back to us to the page handler ajax_graph() whenever
# an update of the graph should be done. It must contain everything that we need to
# create the HTML code of the graph. The entry "graph_id" will be set by the javascript
# code since it is not known to us.
class GraphRenderState(BaseModel):
    """Round-trip envelope sent to the browser and echoed back on graph updates."""

    interaction: GraphInteractionState
    recipe: GraphRecipe
    specification: SerializeAsAny[GraphSpecification]
    display_config: GraphDisplayConfigHTML
    display_id: str = ""
    onclick: str | None = None

    @field_validator("specification", mode="before")
    @classmethod
    def _parse_specification(cls, value: object) -> GraphSpecification:
        if isinstance(value, GraphSpecification):
            return value
        return parse_graph_specification(value)


class GraphHoverRequest(BaseModel):
    """Slim request model for ajax_graph_values_at_time.

    Only the recipe and interaction are needed to serve hover data; the
    specification, display_config and other fields carried by GraphRenderState
    are irrelevant and are no longer sent by the browser for this endpoint.
    """

    recipe: GraphRecipe
    interaction: GraphInteractionState


class GraphExportRequest(BaseModel, frozen=True):
    """Typed model for the request sent to graph_export.py and graph_image.py.

    Also stored as popup_data[2] for the graph 'Add to' and export actions.
    The browser forwards the whole object as the ?request= parameter when the
    user picks "Export as JSON" or "Export as PNG"; add-to backends (dashboard,
    report, graph collection, custom graph) only consume specification.
    """

    # Identifies which graph to render; consumed by every backend.
    specification: SerializeAsAny[GraphSpecification]
    # Forwarded to graph_export/graph_image; unused by add-to backends.
    consolidation_function: GraphConsolidationFunction = "max"
    # Forwarded to graph_export/graph_image; defaults to 25 h ago when None.
    time_start: int | None = None
    # Forwarded to graph_export/graph_image; defaults to now when None.
    time_end: int | None = None

    @field_validator("specification", mode="before")
    @classmethod
    def _parse_specification(cls, value: object) -> GraphSpecification:
        if isinstance(value, GraphSpecification):
            return value
        return parse_graph_specification(value)


def _load_graph_pin() -> int | None:
    raw_pin_time = user.load_file("graph_pin", None)
    return None if raw_pin_time is None else int(raw_pin_time)


def _save_graph_pin(request: Request) -> None:
    try:
        pin_timestamp = request.get_integer_input("pin")
    except ValueError:
        pin_timestamp = None
    user.save_file("graph_pin", None if pin_timestamp == -1 else pin_timestamp)


def _order_graph_curves_for_legend_and_mouse_hover[TCurveType: (LayoutedCurve, Curve)](
    curves: Sequence[TCurveType],
    curve_annotations: Sequence[CurveAnnotations],
) -> Sequence[tuple[TCurveType, CurveAnnotations]]:
    """
    CMK-22181
    Graph(
        compound_lines = [
            "compound-1",
            "compound-2",
        ],
        simple_lines = [
            "simple-1",
            "simple-2",
            Sum(["compound-1", "compound-2"]),
        ],
    )
    Legend:
    - Sum of compound-1 & compound-2
    - simple-2
    - simple-1
    - compound-2
    - compound-1

    Bidirectional(
        lower = Graph(
            compound_lines = [
                "lower-compound-1",
                "lower-compound-2",
            ],
            simple_lines = [
                "lower-simple-1",
                "lower-simple-2",
                Sum(["lower-compound-1", "lower-compound-2"]),
            ],
        ),
        upper = Graph(
            compound_lines = [
                "upper-compound-1",
                "upper-compound-2",
            ],
            simple_lines = [
                "upper-simple-1",
                "upper-simple-2",
                Sum(["upper-compound-1", "upper-compound-2"]),
            ],
        ),
    )
    Legend:
    - Sum of upper-compound-1 & upper-compound-2
    - upper-simple-2
    - upper-simple-1
    - upper-compound-2
    - upper-compound-1
    - lower-compound-1
    - lower-compound-2
    - lower-simple-1
    - lower-simple-2
    - Sum of lower-compound-1 & lower-compound-2
    """
    assert len(curves) == len(curve_annotations)
    lines: list[tuple[TCurveType, CurveAnnotations]] = []
    areas: list[tuple[TCurveType, CurveAnnotations]] = []
    mirrored_lines: list[tuple[TCurveType, CurveAnnotations]] = []
    mirrored_areas: list[tuple[TCurveType, CurveAnnotations]] = []
    refs: list[tuple[TCurveType, CurveAnnotations]] = []
    for curve, curve_annotation in zip(curves, curve_annotations):
        match line_type := curve["line_type"]:
            case "line":
                target = lines
            case "-line":
                target = mirrored_lines
            case "area" | "stack":
                target = areas
            case "-area" | "-stack":
                target = mirrored_areas
            case "ref":
                target = refs
            case _:
                raise ValueError(line_type)
        target.append((curve, curve_annotation))
    return lines[::-1] + areas[::-1] + mirrored_areas + mirrored_lines + refs


def make_graph_time_range_html(
    *,
    start: int,
    end: int,
    factor: int,
    height_in_ex: float,
) -> GraphTimeRange:
    return GraphTimeRange(
        start=start,
        end=end,
        step=factor * int((end - start) / (height_in_ex * _HTML_SIZE_PER_EX * 4)),
    )


def _user_graph_time_range_file_name(custom_graph_id: str) -> UserGraphTimeRangeFileName:
    if "../" in custom_graph_id:
        raise ValueError("../ in graph id")
    return UserGraphTimeRangeFileName(f"graph_range_{custom_graph_id}")


class UserGraphTimeRangeStore:
    def __init__(self, user_id: UserId) -> None:
        self.user_id = user_id

    def save(self, custom_graph_id: str, time_range: GraphTimeRange) -> None:
        save_user_file(
            _user_graph_time_range_file_name(custom_graph_id),
            time_range.model_dump(),
            self.user_id,
        )

    def load(self, custom_graph_id: str) -> GraphTimeRange | None:
        return (
            GraphTimeRange.model_validate(raw_range)
            if (
                raw_range := load_user_file(
                    _user_graph_time_range_file_name(custom_graph_id),
                    self.user_id,
                    deflt=None,
                    lock=False,
                )
            )
            else None
        )

    def remove(self, custom_graph_id: str) -> None:
        (
            profile_dir / self.user_id / f"{_user_graph_time_range_file_name(custom_graph_id)}.mk"
        ).unlink(missing_ok=True)


#   .--HTML-Graphs---------------------------------------------------------.
#   |                      _   _ _____ __  __ _                            |
#   |                     | | | |_   _|  \/  | |                           |
#   |                     | |_| | | | | |\/| | |                           |
#   |                     |  _  | | | | |  | | |___                        |
#   |                     |_| |_| |_| |_|  |_|_____|                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Code for rendering a graph in HTML.                                 |
#   '----------------------------------------------------------------------'

# Code paths for rendering graphs in HTML:

# View -> Painter
# View -> Icons -> Hover
# Dashboard -> Embedded Graph
# Javascript Interactive Graph
# Graph Collection
# Graph Overview
# Custom graph

# TODO: This is not acurate! Rendering of the graphs is wrong especially when the font size is changed
# this does not lead to correct results. We should find a way to fix this. Otherwise the font size
# chaning of the graph rendering options won't work as expected.
_HTML_SIZE_PER_EX = 11.0
_MIN_RESIZE_WIDTH = 50
_MIN_RESIZE_HEIGHT = 6

# Minimum canvas height below which a widget is too small to render a graph with legend.
_MIN_WIDGET_HEIGHT_EX = 11


def render_graph_error_html(*, title: str, msg_or_exc: Exception | str, debug: bool) -> HTML:
    if isinstance(msg_or_exc, MKGeneralException) and not debug:
        msg = "%s" % msg_or_exc

    elif isinstance(msg_or_exc, Exception):
        if debug:
            raise msg_or_exc
        msg = traceback.format_exc()
    else:
        msg = msg_or_exc

    return HTMLWriter.render_div(
        HTMLWriter.render_div(title, class_="title") + HTMLWriter.render_pre(msg),
        class_=["graph", "brokengraph"],
    )


def _collect_graph_html(
    request: Request,
    render_state: GraphRenderState,
    artwork: GraphArtwork,
    annotations: GraphArtworkAnnotations,
    expandable_legend_appearance: ExpandableLegendAppearance,
    additional_html: AdditionalGraphHTML | None = None,
) -> HTML:
    with output_funnel.plugged():
        display_config = render_state.display_config
        html.open_div(
            class_=["graph"]
            + (["preview"] if display_config.preview else [])
            + (["with_margin"] if display_config.show_margin else []),
            style=f"font-size: {display_config.font_size:.1f}pt;",
        )

        if display_config.show_controls:
            # Data will be transferred via URL and Javascript magic eventually
            # to our function popup_add_element (htdocs/reporting.py)
            # argument report_name --> provided by popup system
            # further arguments:
            html.popup_trigger(
                content=html.render_static_icon(StaticIcon(IconNames.menu), title=_("Add to ...")),
                ident="add_visual",
                method=MethodAjax(endpoint="add_visual", url_vars=[("add_type", "pnpgraph")]),
                data=[
                    "pnpgraph",
                    None,
                    GraphExportRequest(
                        specification=render_state.specification,
                        consolidation_function=(
                            render_state.interaction.consolidation_function or "max"
                        ),
                        time_start=render_state.interaction.time_start,
                        time_end=render_state.interaction.time_end,
                    ).model_dump(),
                ],
                style="z-index:2",
            )  # Ensures that graph canvas does not cover it

        v_axis_label = artwork.y_axis["unit_label"]
        if v_axis_label:
            html.div(v_axis_label, class_="v_axis_label")

        if display_config.show_controls and display_config.resizable:
            html.img(src=theme.detect_icon_path("resize_graph", prefix=""), class_="resize")

        # Render title and time info together so they can be laid out without overlapping.
        # The canvas pixel width is computed here so the header div can carry an explicit width,
        # which is the only reliable way to constrain a flex container inside an inline-block and
        # thus allow the title to wrap when title + time info would exceed the canvas width.
        is_inline = display_config.show_title == "inline"
        graph_width: float = render_state.interaction.size_x * _HTML_SIZE_PER_EX
        time_text: str | None = None
        if display_config.show_graph_time and not display_config.preview:
            time_text = annotations.x_axis_title or ""

        title = text_with_links_to_user_translated_html(
            [
                (element.text, element.url)
                for element in iter_graph_title_elements(
                    request,
                    render_state.specification,
                    render_state.recipe.title,
                    display_config,
                    explicit_title=display_config.explicit_title,
                )
            ],
            separator=HTML.without_escaping(" / "),
        )

        if title or time_text is not None:
            # For the inline variant the width is already constrained by CSS (left:0; right:18px).
            # For the non-inline variant we must set it explicitly so the flex container has a
            # definite size and the title can wrap instead of stretching the parent inline-block.
            header_style = None if is_inline else f"width: {int(graph_width)}px;"
            html.open_div(
                class_=["graph_header"] + (["inline"] if is_inline else []),
                style=header_style,
            )
            if title:
                html.div(title, class_="title")
            if time_text is not None:
                html.div(time_text, class_="time")
            html.close_div()

        # Create canvas where actual graph will be rendered
        graph_height: float = render_state.interaction.size_y * _HTML_SIZE_PER_EX
        html.canvas(
            "",
            style="position: relative; width: %dpx; height: %dpx;" % (graph_width, graph_height),
            width=str(graph_width * 2),
            height=str(graph_height * 2),
        )

        # Note: due to "omit_zero_metrics" the graph might not have any curves
        if display_config.show_legend and artwork.curves:
            _show_graph_legend(
                render_state.interaction.consolidation_function,
                artwork,
                annotations,
                display_config,
                expandable_legend_appearance,
                render_state.interaction.size_x,
            )

        if additional_html:
            html.open_div(align="center")
            html.h2(additional_html.title)
            html.write_html(HTML.without_escaping(additional_html.html))
            html.close_div()

        html.close_div()
        return HTML.without_escaping(output_funnel.drain())


# Render the complete HTML code of a graph - including its <div> container.
# Later updates will just replace the content of that container.
def _create_javascript_graph(
    request: Request,
    render_state: GraphRenderState,
    artwork: GraphArtwork,
    annotations: GraphArtworkAnnotations,
    expandable_legend_appearance: ExpandableLegendAppearance,
    additional_html: AdditionalGraphHTML | None = None,
) -> HTML:
    return HTMLWriter.render_javascript(
        "cmk.graphs.create_graph(%s, %s, %s);"
        % (
            json.dumps(
                str(
                    _collect_graph_html(
                        request,
                        render_state,
                        artwork,
                        annotations,
                        expandable_legend_appearance,
                        additional_html,
                    )
                )
            ),
            json.dumps(artwork.model_dump()),
            json.dumps(render_state.model_dump()),
        )
    )


def _render_time_range_selection(
    request: Request,
    render_state: GraphRenderState,
    *,
    graph_timeranges: Sequence[GraphTimerange],
    temperature_unit: TemperatureUnit,
    backend_time_series_fetcher: FetchTimeSeries | None,
    expandable_legend_appearance: ExpandableLegendAppearance,
) -> HTML:
    now = int(time.time())
    rows = []
    for timerange_attrs in graph_timeranges:
        duration = timerange_attrs["duration"]
        assert isinstance(duration, int)

        preview_config = render_state.display_config.model_copy(
            update={
                "font_size": SizePT(6.0),
                "fixed_timerange": True,  # Do not follow timerange changes of other graphs
                "explicit_title": timerange_attrs["title"],
                "show_legend": False,
                "show_controls": False,
                "preview": True,
                "resizable": False,
                "interaction": False,
            }
        )

        preview_size = (20.0, 4.0)
        time_range = make_graph_time_range_html(
            start=now - duration,
            end=now,
            factor=2,
            height_in_ex=preview_size[1],
        )

        preview_interaction = render_state.interaction.model_copy(
            update={
                "time_start": time_range.start,
                "time_end": time_range.end,
                "step": time_range.step,
                "size_x": preview_size[0],
                "size_y": preview_size[1],
            }
        )
        preview_state = render_state.model_copy(
            update={
                "interaction": preview_interaction,
                "display_config": preview_config,
                "onclick": "cmk.graphs.change_graph_timerange(graph, %d)" % duration,
            }
        )

        artwork_or_errors = compute_graph_artwork(
            render_state.recipe,
            time_range,
            preview_size,
            metrics_from_api,
            consolidation_function=render_state.interaction.consolidation_function,
            temperature_unit=temperature_unit,
            backend_time_series_fetcher=backend_time_series_fetcher,
            pin_time=_load_graph_pin(),
        )
        rows.append(
            HTMLWriter.render_td(
                _create_javascript_graph(
                    request,
                    preview_state,
                    artwork_or_errors.artwork,
                    artwork_or_errors.annotations,
                    expandable_legend_appearance,
                ),
                title=_("Change graph time range to: %s") % timerange_attrs["title"],
            )
        )
    return HTMLWriter.render_table(
        HTML.empty().join(HTMLWriter.render_tr(content) for content in rows),
        class_="timeranges",
    )


def _render_graph_content_html(
    request: Request,
    render_state: GraphRenderState,
    artwork_or_errors: GraphArtworkOrErrors,
    *,
    debug: bool,
    graph_timeranges: Sequence[GraphTimerange],
    temperature_unit: TemperatureUnit,
    backend_time_series_fetcher: FetchTimeSeries | None,
    expandable_legend_appearance: ExpandableLegendAppearance,
    show_limits_if_reached: bool,
    additional_html: AdditionalGraphHTML | None = None,
) -> HTML:
    display_config = render_state.display_config

    if artwork_or_errors.errors:
        if url := render_state.specification.url():
            output = HTMLWriter.render_div(
                _(
                    "Cannot render complete graph. See graph '<a href='%s'>%s</a>' for further details."
                )
                % (url, render_state.recipe.title),
                class_="error",
            )
        else:
            output = HTMLWriter.render_div(
                _("Cannot render complete graph"),
                class_="error",
            )
        size_y_offset = -6
    else:
        output = HTML.empty()
        size_y_offset = 0

    if show_limits_if_reached and artwork_or_errors.graph_metric_limits_reached:
        if url := render_state.specification.url():
            output += HTMLWriter.render_div(
                _(
                    "The result of your query hit the maximum number of %s time series."
                    " Please narrow down your query."
                    " See graph '<a href='%s'>%s</a>' for further details."
                )
                % (
                    max(
                        limit.max_series_per_query
                        for limit in artwork_or_errors.graph_metric_limits_reached
                    ),
                    url,
                    render_state.recipe.title,
                ),
                class_="warning",
            )
        else:
            output += HTMLWriter.render_div(
                _(
                    "The result of your query hit the maximum number of %s time series."
                    " Please narrow down your query."
                )
                % max(
                    limit.max_series_per_query
                    for limit in artwork_or_errors.graph_metric_limits_reached
                ),
                class_="warning",
            )
        size_y_offset -= 8

    if size_y_offset != 0:
        render_state = render_state.model_copy(
            update={
                "interaction": render_state.interaction.model_copy(
                    update={"size_y": render_state.interaction.size_y + size_y_offset}
                )
            }
        )

    try:
        output += _create_javascript_graph(
            request,
            render_state,
            artwork_or_errors.artwork,
            artwork_or_errors.annotations,
            expandable_legend_appearance,
            additional_html,
        )
        if display_config.show_time_range_previews:
            return HTMLWriter.render_div(
                output
                + _render_time_range_selection(
                    request,
                    render_state,
                    graph_timeranges=graph_timeranges,
                    temperature_unit=temperature_unit,
                    backend_time_series_fetcher=backend_time_series_fetcher,
                    expandable_legend_appearance=expandable_legend_appearance,
                ),
                class_="graph_with_timeranges",
            )
        return output

    except MKLivestatusNotFoundError:
        return render_graph_error_html(
            title=_("Cannot create graph"),
            msg_or_exc=_("Cannot fetch data via Livestatus"),
            debug=debug,
        )

    except Exception as e:
        return render_graph_error_html(
            title=_("Cannot create graph"),
            msg_or_exc=e,
            debug=debug,
        )


def _compute_recipes(
    graph_specification: GraphSpecification,
    env: GraphEnvironment,
) -> Sequence[GraphRecipeWithOverrides] | HTML:
    try:
        return graph_specification.recipes(env, graph_specification.fetch_graph_rows(env))
    except MKLivestatusNotFoundError:
        return render_graph_error_html(
            title=_("Cannot calculate graph recipes"),
            msg_or_exc="%s\n\n%s: %r"
            % (
                _("Cannot fetch data via Livestatus"),
                _("The graph specification is"),
                graph_specification,
            ),
            debug=env.debug,
        )
    except Exception as e:
        return render_graph_error_html(
            title=_("Cannot calculate graph recipes"),
            msg_or_exc=e,
            debug=env.debug,
        )


@tracer.instrument("graphing.render_graphs_html")
def render_graphs_html(
    graph_specification: GraphSpecification,
    time_range: GraphTimeRange,
    display_config: GraphDisplayConfigHTML,
    env: GraphEnvironment,
    *,
    size: tuple[float, float],
    graph_timeranges: Sequence[GraphTimerange],
    display_id: str = "",
) -> HTML:
    """Render graph content synchronously without AJAX."""
    if isinstance(recipes := _compute_recipes(graph_specification, env), HTML):
        return recipes

    output = HTML.empty()
    for recipe_with_overrides in recipes:
        effective_time_range = recipe_with_overrides.time_range or time_range
        interaction = GraphInteractionState(
            consolidation_function=recipe_with_overrides.consolidation_function,
            time_start=effective_time_range.start,
            time_end=effective_time_range.end,
            step=effective_time_range.step,
            value_min=(
                effective_time_range.vertical_range[0]
                if effective_time_range.vertical_range
                else None
            ),
            value_max=(
                effective_time_range.vertical_range[1]
                if effective_time_range.vertical_range
                else None
            ),
            size_x=size[0],
            size_y=size[1],
        )
        render_state = GraphRenderState(
            interaction=interaction,
            recipe=recipe_with_overrides.recipe,
            specification=recipe_with_overrides.specification,
            display_config=display_config.update_from_options(recipe_with_overrides.render_options),
            display_id=display_id,
        )
        output += _render_graph_content_html(
            request,
            render_state,
            compute_graph_artwork(
                render_state.recipe,
                effective_time_range,
                (interaction.size_x, interaction.size_y),
                metrics_from_api,
                consolidation_function=interaction.consolidation_function,
                temperature_unit=env.temperature_unit,
                backend_time_series_fetcher=env.backend_time_series_fetcher,
                pin_time=_load_graph_pin(),
                mark_requested_end_time=recipe_with_overrides.mark_requested_end_time,
            ),
            debug=env.debug,
            graph_timeranges=graph_timeranges,
            temperature_unit=env.temperature_unit,
            backend_time_series_fetcher=env.backend_time_series_fetcher,
            expandable_legend_appearance=ExpandableLegendAppearance.FOLDABLE,
            show_limits_if_reached=False,
            additional_html=recipe_with_overrides.additional_html,
        )
    return output


@tracer.instrument("graphing.host_service_graph_popup_cmk")
def host_service_graph_popup_cmk(
    site: SiteId | None,
    host_name: HostName,
    service_description: ServiceName,
    env: GraphEnvironment,
    *,
    graph_timeranges: Sequence[GraphTimerange],
) -> None:
    end_time = int(time.time())
    start_time = end_time - 8 * 3600
    popup_size = (30.0, 10.0)
    display_config = GraphDisplayConfigHTML.from_user_context_and_options(
        user,
        theme.get(),
        GraphRenderOptions(
            font_size=SizePT(6.0),
            resizable=False,
            show_controls=False,
            show_legend=False,
            interaction=False,
            show_time_range_previews=False,
        ),
    )
    html.write_html(
        render_graphs_html(
            get_template_graph_specification(
                site_id=site,
                host_name=host_name,
                service_name=service_description,
            ),
            make_graph_time_range_html(
                start=start_time,
                end=end_time,
                factor=1,
                height_in_ex=popup_size[1],
            ),
            display_config,
            env,
            size=popup_size,
            graph_timeranges=graph_timeranges,
        )
    )


def _show_pin_time(artwork: GraphArtwork, config: GraphDisplayConfigHTML) -> bool:
    if not config.show_pin:
        return False

    timestamp = artwork.pin_time
    return (
        timestamp is not None and artwork.actual_time.start <= timestamp <= artwork.actual_time.end
    )


def _render_pin_time_label(artwork: GraphArtwork) -> str:
    timestamp = artwork.pin_time
    return cmk.utils.render.date_and_time(timestamp)[:-3]


@dataclass(frozen=True)
class _LegendTitle:
    type: Literal["min", "max", "average", "last", "pin"]
    title: str
    inactive: bool
    description: str


def _compute_legend_titles(
    consolidation_function: GraphConsolidationFunction | None,
    artwork: GraphArtwork,
    display_config: GraphDisplayConfigHTML,
) -> Generator[_LegendTitle]:
    step = artwork.actual_time.step

    def _inactive_descr(scalar_type: str) -> str:
        if consolidation_function is None or step == 60:
            return ""
        return (
            _(
                'This graph is based on data consolidated with the function "%s". The '
                'values in this column are the "%s" values of the "%s" values '
                "aggregated in %s steps. Assuming a check interval of 1 minute, the %s "
                "values here are based on the %s value out of %d raw values."
            )
            % (
                consolidation_function,
                scalar_type,
                consolidation_function,
                get_step_label(step),
                scalar_type,
                consolidation_function,
                (step / 60),
            )
            + "\n\n"
            + _('Click here to change the graphs consolidation function to "%s".') % scalar_type
        )

    yield _LegendTitle(
        "min",
        _("Minimum"),
        consolidation_function is not None and consolidation_function != "min",
        _inactive_descr("min"),
    )
    yield _LegendTitle(
        "max",
        _("Maximum"),
        consolidation_function is not None and consolidation_function != "max",
        _inactive_descr("max"),
    )
    yield _LegendTitle(
        "average",
        _("Average"),
        consolidation_function is not None and consolidation_function != "average",
        _inactive_descr("average"),
    )
    yield _LegendTitle("last", _("Last"), False, "")
    if _show_pin_time(artwork, display_config):
        yield _LegendTitle("pin", _render_pin_time_label(artwork), False, "")


def _compute_graph_legend_styles(
    display_config: GraphDisplayConfigHTML, size_x: float
) -> Iterator[str]:
    """Render legend that describe the metrics"""
    graph_width = size_x * _HTML_SIZE_PER_EX

    if display_config.show_vertical_axis or display_config.show_controls:
        legend_margin_left = 49
    else:
        legend_margin_left = 0

    legend_width = graph_width - legend_margin_left

    yield "width:%dpx" % legend_width

    if legend_margin_left:
        yield "margin-left:%dpx" % legend_margin_left


def _sort_attributes_by_type(attribute_type: Literal["resource", "scope", "data_point"]) -> int:
    match attribute_type:
        case "resource":
            return 0
        case "scope":
            return 1
        case "data_point":
            return 2
        case other:
            assert_never(other)


def _readable_attribute_type(attribute_type: Literal["resource", "scope", "data_point"]) -> str:
    match attribute_type:
        case "resource":
            return _("Resource")
        case "scope":
            return _("Scope")
        case "data_point":
            return _("Data point")
        case other:
            assert_never(other)


@dataclass(frozen=True, kw_only=True)
class _Attribute:
    name: str
    value: str
    type: str


def _render_attributes(
    table_uuid_str: str,
    graph_legend_styles: Sequence[str],
    attributes: Sequence[_Attribute],
) -> HTML:
    with output_funnel.plugged():
        html.open_table(
            class_="legend",
            style=(
                list(graph_legend_styles)
                + [
                    "display: none",
                    "margin-top: 0px",
                    "margin-bottom: 10px",
                    "margin-right: 0px",
                    "margin-left: 18px",
                    "border-spacing: 5px",
                ]
            ),
            id=table_uuid_str,
        )

        html.open_thead()
        html.open_tr()
        html.th(_("Attribute name"), style="text-align: left; width: 20%;")
        html.th(_("Attribute value"), style="text-align: left")
        html.th(_("Attribute type"), style="text-align: left; width: 10%;")
        html.close_tr()
        html.close_thead()

        html.open_tbody()
        for attribute in attributes:
            html.open_tr()
            html.td(attribute.name)
            html.td(attribute.value)
            html.td(attribute.type)
            html.close_tr()

        html.close_tbody()
        html.close_table()

        return HTML.without_escaping(output_funnel.drain())


@dataclass(frozen=True)
class _LegendCurveRow:
    curve: LayoutedCurve
    curve_ann: CurveAnnotations
    attributes: Sequence[_Attribute]
    table_uuid: str


def _compute_legend_curve_rows(
    artwork: GraphArtwork,
    annotations: GraphArtworkAnnotations,
) -> Iterator[_LegendCurveRow]:
    for curve, curve_ann in _order_graph_curves_for_legend_and_mouse_hover(
        artwork.curves, annotations.curves
    ):
        yield _LegendCurveRow(
            curve=curve,
            curve_ann=curve_ann,
            attributes=[
                _Attribute(name=name, value=value, type=_readable_attribute_type(ty))
                for ty, attrs in sorted(
                    curve_ann.attributes.items(), key=lambda t: _sort_attributes_by_type(t[0])
                )
                for name, value in attrs.items()
            ],
            table_uuid=str(uuid4()),
        )


def _show_graph_legend(
    consolidation_function: GraphConsolidationFunction | None,
    artwork: GraphArtwork,
    annotations: GraphArtworkAnnotations,
    display_config: GraphDisplayConfigHTML,
    expandable_legend_appearance: ExpandableLegendAppearance,
    size_x: float,
) -> None:
    font_size_style = "font-size: %dpt;" % display_config.font_size
    legend_titles = list(_compute_legend_titles(consolidation_function, artwork, display_config))
    graph_legend_styles = list(_compute_graph_legend_styles(display_config, size_x))

    html.open_div(
        class_=["legend_container"],
        style=(
            [
                f"max-height: {display_config.legend_max_height_px}px",
                "overflow-y: auto",
            ]
            if display_config.legend_max_height_px
            else []
        ),
    )
    html.open_table(class_="legend", style=graph_legend_styles)
    html.open_thead()
    html.open_tr()
    html.th("")
    for legend_title in legend_titles:
        classes = ["scalar", legend_title.type]
        if legend_title.inactive:
            classes.append("inactive")
        html.th(
            legend_title.title,
            class_=classes,
            style=font_size_style,
            title=legend_title.description,
        )
    html.close_tr()
    html.close_thead()

    # Render the curve related rows
    html.open_tbody()
    for row in _compute_legend_curve_rows(artwork, annotations):
        html.open_tr()

        if row.attributes:
            match expandable_legend_appearance:
                case ExpandableLegendAppearance.POP_UP:
                    html.open_td(
                        style=[font_size_style],
                        class_=["with_attributes"],
                        onmouseover=f"cmk.graphs.showAttributes(event, '{row.curve['title']}', {json.dumps([_('Name'), _('Value'), _('Type')])}, {json.dumps([asdict(attr) for attr in row.attributes])})",
                        onmouseleave="cmk.graphs.hideAttributes()",
                    )
                case ExpandableLegendAppearance.FOLDABLE:
                    html.open_td(
                        style=[font_size_style],
                        class_=["with_attributes"],
                        onclick=f"const el = document.getElementById('{row.table_uuid}'); el.style.display = (el.style.display === 'none' || el.style.display === '') ? 'block' : 'none';",
                    )
        else:
            html.open_td(style=[font_size_style])

        html.write_html(render_color_icon(row.curve["color"]))
        html.write_text_permissive(row.curve["title"])
        html.close_td()

        for legend_title in legend_titles:
            if legend_title.type == "pin" and not _show_pin_time(artwork, display_config):
                continue

            classes = ["scalar"]
            if legend_title.inactive:
                classes.append("inactive")

            html.td(
                row.curve_ann.scalars[legend_title.type][1],
                class_=classes,
                style=font_size_style,
            )

        html.close_tr()

        if row.attributes and expandable_legend_appearance is ExpandableLegendAppearance.FOLDABLE:
            html.open_tr()
            html.open_td(style=font_size_style, colspan=len(legend_titles) + 1)
            html.write_html(_render_attributes(row.table_uuid, graph_legend_styles, row.attributes))
            html.close_td()
            html.close_tr()

    # Render scalar values
    if artwork.horizontal_rules:
        first = True
        for horizontal_rule in artwork.horizontal_rules:
            html.open_tr(class_=["scalar"] + (["first"] if first else []))
            html.open_td(style=font_size_style)
            html.write_html(render_color_icon(horizontal_rule.color))
            html.write_text_permissive(str(horizontal_rule.title))
            html.close_td()

            # A colspan of 5 has to be used here, since the pin that is added by a click into
            # the graph introduces a new column.
            html.td(
                horizontal_rule.rendered_value,
                colspan=5,
                class_="scalar",
                style=font_size_style,
            )
            html.close_tr()
            first = False

    html.close_tbody()
    html.close_table()
    html.close_div()


@dataclass(frozen=True, kw_only=True)
class Bounds:
    top: int
    right: int
    bottom: int
    left: int


def _graph_margin_ex(
    show_margin: bool,
    *,
    top: int = 8,
    right: int = 8,
    bottom: int = 8,
    left: int = 8,
) -> Bounds:
    return (
        Bounds(
            top=int(round(top / _HTML_SIZE_PER_EX)),
            right=int(round(right / _HTML_SIZE_PER_EX)),
            bottom=int(round(bottom / _HTML_SIZE_PER_EX)),
            left=int(round(left / _HTML_SIZE_PER_EX)),
        )
        if show_margin
        else Bounds(
            top=0,
            right=0,
            bottom=0,
            left=0,
        )
    )


def _parse_consolidation_function(raw: str | None) -> GraphConsolidationFunction | None:
    match raw:
        case "max":
            return "max"
        case "min":
            return "min"
        case "average":
            return "average"
        case _:
            return None


@tracer.instrument("graphing.render_graph_html")
def render_graph_html(
    request: Request,
    render_state: GraphRenderState,
    registered_metrics: Mapping[str, RegisteredMetric],
    *,
    temperature_unit: TemperatureUnit,
    backend_time_series_fetcher: FetchTimeSeries | None,
    show_titles_if_limit_reached: bool,
    converter: Callable[[GraphMetricExpression], JsonSerializable] | None,
    additional_html: AdditionalGraphHTML | None = None,
    graph_timeranges: Sequence[GraphTimerange] | None = None,
) -> JsonSerializable:
    interaction = render_state.interaction
    display_config = render_state.display_config

    start_time_var = request.var("start_time")
    end_time_var = request.var("end_time")
    step_var = request.var("step")
    if start_time_var is not None and end_time_var is not None and step_var is not None:
        start_time = int(float(start_time_var))
        end_time = int(float(end_time_var))
        # since step can be relatively small, we round
        step: int | str = int(round(float(step_var)))
    else:
        start_time, end_time = interaction.time_start, interaction.time_end
        step = interaction.step

    resize_x_var = request.var("resize_x")
    resize_y_var = request.var("resize_y")

    if resize_x_var is not None and resize_y_var is not None:
        size_x = max(
            _MIN_RESIZE_WIDTH, float(resize_x_var) / _HTML_SIZE_PER_EX + interaction.size_x
        )
        size_y = max(
            _MIN_RESIZE_HEIGHT, float(resize_y_var) / _HTML_SIZE_PER_EX + interaction.size_y
        )
        user.save_file("graph_size", (size_x, size_y))
    else:
        size_x = interaction.size_x
        size_y = interaction.size_y

    range_from_var = request.var("range_from")
    range_to_var = request.var("range_to")
    if range_from_var is not None and range_to_var is not None:
        vertical_range_min: float | None = float(range_from_var)
        vertical_range_max: float | None = float(range_to_var)
    else:
        vertical_range_min = interaction.value_min
        vertical_range_max = interaction.value_max

    if request.has_var("pin"):
        _save_graph_pin(request)

    if raw_consolidation_function := request.var("consolidation_function"):
        consolidation_function = _parse_consolidation_function(raw_consolidation_function)
    else:
        consolidation_function = interaction.consolidation_function

    interaction = GraphInteractionState(
        graph_id=interaction.graph_id,
        consolidation_function=consolidation_function,
        time_start=start_time,
        time_end=end_time,
        step=step,
        value_min=vertical_range_min,
        value_max=vertical_range_max,
        size_x=size_x,
        size_y=size_y,
    )

    # Persist the current data range for the graph editor.
    if display_config.editing and (render_state.specification.id):
        assert user.id is not None
        UserGraphTimeRangeStore(user.id).save(
            render_state.specification.id,
            GraphTimeRange(
                start=start_time,
                end=end_time,
                step=step,
                vertical_range=(
                    (vertical_range_min, vertical_range_max)
                    if vertical_range_min is not None and vertical_range_max is not None
                    else None
                ),
            ),
        )

    render_state = render_state.model_copy(update={"interaction": interaction})

    artwork_or_errors = compute_graph_artwork(
        render_state.recipe,
        GraphTimeRange(
            start=interaction.time_start,
            end=interaction.time_end,
            step=interaction.step,
            vertical_range=(
                (interaction.value_min, interaction.value_max)
                if interaction.value_min is not None and interaction.value_max is not None
                else None
            ),
        ),
        (interaction.size_x, interaction.size_y),
        registered_metrics,
        consolidation_function=interaction.consolidation_function,
        temperature_unit=temperature_unit,
        backend_time_series_fetcher=backend_time_series_fetcher,
        pin_time=_load_graph_pin(),
    )

    if artwork_or_errors.errors:
        error_msg = _(
            "Error while querying the following metrics: %s."
            "<br>Last error message: %s."
            "<br>See web.log for further details."
        ) % (
            ", ".join(f"{k.metric_name!r}" for e in artwork_or_errors.errors for k in e.keys),
            str(artwork_or_errors.errors[-1].exception),
        )
    else:
        error_msg = ""

    if artwork_or_errors.graph_metric_limits_reached:
        if show_titles_if_limit_reached:
            warning_msg = _(
                "The result of your query hit the maximum number of %s time series."
                " Please narrow down your queries for the following metrics: %s"
            ) % (
                max(
                    limit.max_series_per_query
                    for limit in artwork_or_errors.graph_metric_limits_reached
                ),
                ", ".join(
                    f"{limit.graph_metric.title!r}"
                    for limit in artwork_or_errors.graph_metric_limits_reached
                ),
            )
        else:
            warning_msg = _(
                "The result of your query hit the maximum number of %s time series."
                " Please narrow down your query."
            ) % max(
                limit.max_series_per_query
                for limit in artwork_or_errors.graph_metric_limits_reached
            )
    else:
        warning_msg = ""

    return {
        "html": str(
            _collect_graph_html(
                request,
                render_state,
                artwork_or_errors.artwork,
                artwork_or_errors.annotations,
                ExpandableLegendAppearance.FOLDABLE,
                additional_html,
            )
        ),
        "graph": artwork_or_errors.artwork.model_dump(),
        "context": render_state.model_dump(),
        "error": error_msg,
        "warning": warning_msg,
        "preview_html": (
            str(
                _render_time_range_selection(
                    request,
                    render_state,
                    graph_timeranges=graph_timeranges,
                    temperature_unit=temperature_unit,
                    backend_time_series_fetcher=backend_time_series_fetcher,
                    expandable_legend_appearance=ExpandableLegendAppearance.FOLDABLE,
                )
            )
            if graph_timeranges is not None and render_state.display_config.show_time_range_previews
            else None
        ),
        "queries_reached_limit": (
            []
            if converter is None
            else [
                c
                for limit in artwork_or_errors.graph_metric_limits_reached
                if (c := converter(limit.graph_metric.operation))
            ]
        ),
    }


# cmk.graphs.load_graph_content will call ajax_render_graph() via JSON to finally load the graph
def _render_deferred_graph_html(
    render_state: GraphRenderState,
    *,
    additional_html: AdditionalGraphHTML | None = None,
) -> HTML:
    # Estimate size of graph. This will not be the exact size of the graph, because
    # this does calculate the size of the canvas area and does not take e.g. the legend
    # into account. We would need the artwork to calculate that, but this is something
    # we don't have in this early stage.
    graph_width = render_state.interaction.size_x * _HTML_SIZE_PER_EX
    graph_height = render_state.interaction.size_y * _HTML_SIZE_PER_EX

    content = HTMLWriter.render_div("", class_="title") + HTMLWriter.render_div(
        "", class_="content", style="width:%dpx;height:%dpx" % (graph_width, graph_height)
    )

    output = HTMLWriter.render_div(
        HTMLWriter.render_div(content, class_=["graph", "loading_graph"]),
        class_="graph_load_container",
    )
    output += HTMLWriter.render_javascript(
        "cmk.graphs.load_graph_content(%s, %s)"
        % (
            json.dumps(render_state.model_dump()),
            json.dumps(additional_html.model_dump() if additional_html else None),
        )
    )

    if "cmk.graphs.register_delayed_graph_listener" not in html.final_javascript_code():
        html.final_javascript("cmk.graphs.register_delayed_graph_listener()")

    return output


# TODO: still relies on the global request object because painters also use this function.
@tracer.instrument("graphing.render_deferred_graphs_html")
def render_deferred_graphs_html(
    graph_specification: GraphSpecification,
    time_range: GraphTimeRange,
    display_config: GraphDisplayConfigHTML,
    env: GraphEnvironment,
    *,
    size: tuple[float, float],
    display_id: str = "",
) -> HTML:
    """Render async AJAX loading containers. JavaScript fills them via ajax_render_graph."""
    if isinstance(recipes := _compute_recipes(graph_specification, env), HTML):
        return recipes

    output = HTML.empty()
    for recipe_with_overrides in recipes:
        effective_time_range = recipe_with_overrides.time_range or time_range
        interaction = GraphInteractionState(
            consolidation_function=recipe_with_overrides.consolidation_function,
            time_start=effective_time_range.start,
            time_end=effective_time_range.end,
            step=effective_time_range.step,
            value_min=(
                effective_time_range.vertical_range[0]
                if effective_time_range.vertical_range
                else None
            ),
            value_max=(
                effective_time_range.vertical_range[1]
                if effective_time_range.vertical_range
                else None
            ),
            size_x=size[0],
            size_y=size[1],
        )
        output += _render_deferred_graph_html(
            GraphRenderState(
                interaction=interaction,
                recipe=recipe_with_overrides.recipe,
                specification=recipe_with_overrides.specification,
                display_config=display_config.update_from_options(
                    recipe_with_overrides.render_options
                ),
                display_id=display_id,
            ),
            additional_html=recipe_with_overrides.additional_html,
        )
    return output


class AjaxRenderGraph(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        """Registered as `ajax_render_graph`.

        Handles both the initial deferred graph load and all subsequent
        interaction updates (drag, zoom, pin, resize).  The JS side always
        POSTs a ``request=<GraphRenderState JSON>`` body; extra interaction
        parameters (``start_time``, ``end_time``, ``step``, ``range_from``,
        ``range_to``, ``resize_x``, ``resize_y``, ``pin``,
        ``consolidation_function``) are sent as additional POST fields and
        consumed directly by :func:`render_graph_html` via the request object.
        """
        api_request = ctx.request.get_request()
        return render_graph_html(
            ctx.request,
            GraphRenderState.model_validate(api_request),
            metrics_from_api,
            temperature_unit=get_temperature_unit(user, ctx.config.default_temperature_unit),
            backend_time_series_fetcher=metric_backend_registry[
                str(edition(paths.omd_root))
            ].get_time_series_fetcher(),
            show_titles_if_limit_reached=False,
            converter=None,
            additional_html=(
                None
                if (raw_additional_html := api_request.get("additional_html")) is None
                else AdditionalGraphHTML.model_validate(raw_additional_html)
            ),
            graph_timeranges=ctx.config.graph_timeranges,
        )


# .
#   .--Graph hover---------------------------------------------------------.
#   |        ____                 _       _                                |
#   |       / ___|_ __ __ _ _ __ | |__   | |__   _____   _____ _ __        |
#   |      | |  _| '__/ _` | '_ \| '_ \  | '_ \ / _ \ \ / / _ \ '__|       |
#   |      | |_| | | | (_| | |_) | | | | | | | | (_) \ V /  __/ |          |
#   |       \____|_|  \__,_| .__/|_| |_| |_| |_|\___/ \_/ \___|_|          |
#   |                      |_|                                             |
#   +----------------------------------------------------------------------+
#   | Processing of the graph hover which shows the current values at the  |
#   | position of the mouse                                                |
#   '----------------------------------------------------------------------'


@tracer.instrument("graphing.render_graph_values_at_time")
def render_graph_values_at_time(
    recipe: GraphRecipe,
    time_range: GraphTimeRange,
    registered_metrics: Mapping[str, RegisteredMetric],
    *,
    consolidation_function: GraphConsolidationFunction | None,
    debug: bool,
    hover_time: int,
    temperature_unit: TemperatureUnit,
    backend_time_series_fetcher: FetchTimeSeries | None,
) -> None:
    """Write the JSON graph hover response for a pre-built recipe and data range."""
    response.set_content_type("application/json")
    try:
        curves = compute_curves_at_timestamp(
            [
                result.ok
                for result in fetch_augmented_time_series(
                    registered_metrics,
                    recipe,
                    time_range,
                    consolidation_function=consolidation_function,
                    temperature_unit=temperature_unit,
                    backend_time_series_fetcher=backend_time_series_fetcher,
                )
                if result.is_ok()
            ],
            user_specific_unit(recipe.unit_spec, temperature_unit).formatter.render,
            hover_time,
        )
        response.set_data(
            json.dumps(
                {
                    "rendered_hover_time": cmk.utils.render.date_and_time(hover_time),
                    "curves": [
                        c
                        for c, _a in _order_graph_curves_for_legend_and_mouse_hover(
                            curves,
                            # TODO Dummy annotations due to zip
                            [
                                CurveAnnotations(
                                    scalars=Scalars(
                                        pin=(None, ""),
                                        last=(None, ""),
                                        max=(None, ""),
                                        min=(None, ""),
                                        average=(None, ""),
                                    ),
                                    attributes={},
                                )
                                for _ in range(len(curves))
                            ],
                        )
                    ],
                }
            )
        )
    except Exception as e:
        logger.error(
            "Ajax call ajax_graph_values_at_time failed: %s\n%s", e, traceback.format_exc()
        )
        if debug:
            raise
        response.set_data("ERROR: %s" % e)


# NOTE
# No AjaxPage, as ajax-pages have a {"result_code": [1|0], "result": ..., ...} result structure,
# while these functions do not have that. In order to preserve the functionality of the JS side
# of things, we keep it.
# TODO: Migrate this to a real AjaxPage
class AjaxGraphValuesAtTime(Page):
    def page(self, ctx: PageContext) -> PageResult:
        """Registered as `ajax_graph_values_at_time`."""
        hover_request = GraphHoverRequest.model_validate(
            json.loads(ctx.request.get_str_input_mandatory("context"))
        )
        render_graph_values_at_time(
            hover_request.recipe,
            GraphTimeRange(
                start=hover_request.interaction.time_start,
                end=hover_request.interaction.time_end,
                step=hover_request.interaction.step,
                vertical_range=(
                    (
                        hover_request.interaction.value_min,
                        hover_request.interaction.value_max,
                    )
                    if hover_request.interaction.value_min is not None
                    and hover_request.interaction.value_max is not None
                    else None
                ),
            ),
            metrics_from_api,
            consolidation_function=hover_request.interaction.consolidation_function,
            debug=ctx.config.debug,
            hover_time=ctx.request.get_integer_input_mandatory("hover_time"),
            temperature_unit=get_temperature_unit(user, ctx.config.default_temperature_unit),
            backend_time_series_fetcher=metric_backend_registry[
                str(edition(paths.omd_root))
            ].get_time_series_fetcher(),
        )
        return None


# .
#   .--Graph Dashlet-------------------------------------------------------.
#   |    ____                 _       ____            _     _      _       |
#   |   / ___|_ __ __ _ _ __ | |__   |  _ \  __ _ ___| |__ | | ___| |_     |
#   |  | |  _| '__/ _` | '_ \| '_ \  | | | |/ _` / __| '_ \| |/ _ \ __|    |
#   |  | |_| | | | (_| | |_) | | | | | |_| | (_| \__ \ | | | |  __/ |_     |
#   |   \____|_|  \__,_| .__/|_| |_| |____/ \__,_|___/_| |_|_|\___|\__|    |
#   |                  |_|                                                 |
#   +----------------------------------------------------------------------+
#   |  This page handler is called by graphs embedded in a dashboard.      |
#   '----------------------------------------------------------------------'


class GraphDestinations:
    dashlet = "dashlet"
    view = "view"
    report = "report"
    notification = "notification"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [
            (GraphDestinations.dashlet, _("Dashboard element")),
            (GraphDestinations.view, _("View")),
            (GraphDestinations.report, _("Report")),
            (GraphDestinations.notification, _("Notification")),
        ]


@tracer.instrument("graphing.host_service_graph_dashlet_cmk")
def host_service_graph_dashlet_cmk(
    request: Request,
    recipes: Sequence[GraphRecipeWithOverrides],
    display_config: GraphDisplayConfigHTML,
    registered_metrics: Mapping[str, RegisteredMetric],
    *,
    debug: bool,
    graph_timeranges: Sequence[GraphTimerange],
    temperature_unit: TemperatureUnit,
    backend_time_series_fetcher: FetchTimeSeries | None,
    display_id: str = "",
    time_range: TimerangeValue = None,
) -> HTML:
    width_var = request.get_float_input_mandatory("width", 0.0)
    width = width_var / _HTML_SIZE_PER_EX

    height_var = request.get_float_input_mandatory("height", 0.0)
    height = height_var / _HTML_SIZE_PER_EX

    bounds = _graph_margin_ex(display_config.show_margin)
    if display_config.show_title not in [False, "inline"]:
        height -= 1
    height -= bounds.top + bounds.bottom
    width -= bounds.left + bounds.right

    if recipes:
        recipe_with_overrides = recipes[0]
    else:
        raise MKGraphRecipeNotFoundError(_("Failed to calculate a graph recipe."))

    time_range = (
        json.loads(request.get_str_input_mandatory("timerange"))
        if time_range is None
        else time_range
    )

    end_time: float
    start_time: float
    # Age and Range like ["age", 300] and ['date', [1661896800, 1661896800]]
    if isinstance(time_range, list):
        # compute_range needs tuple for computation
        timerange_tuple: TimerangeValue = (time_range[0], time_range[1])
        start_time, end_time = Timerange.compute_range(timerange_tuple).range
    # Age like 14400 and y1, d1,...
    else:
        start_time, end_time = Timerange.compute_range(time_range).range

    try:
        graph_time_range = make_graph_time_range_html(
            start=start_time,
            end=end_time,
            factor=1,
            height_in_ex=height,
        )
    except ZeroDivisionError:
        return HTML("", escape=False)

    artwork_or_errors = compute_graph_artwork(
        recipe_with_overrides.recipe,
        graph_time_range,
        (width, height),
        registered_metrics,
        consolidation_function=recipe_with_overrides.consolidation_function,
        temperature_unit=temperature_unit,
        backend_time_series_fetcher=backend_time_series_fetcher,
        pin_time=_load_graph_pin(),
        mark_requested_end_time=recipe_with_overrides.mark_requested_end_time,
    )

    # When the legend is enabled, we need to reduce the height by the height of the legend to
    # make the graph fit into the dashlet area. In preview mode, the Vue scroll container
    # handles legend overflow, so we skip the height reduction.
    is_preview = display_id.endswith("-preview")
    if display_config.show_legend and artwork_or_errors.artwork.curves and not is_preview:
        if height <= _MIN_WIDGET_HEIGHT_EX:
            raise MKGraphWidgetTooSmallError(
                _("Either increase the widget height or disable the graph legend.")
            )

        # Estimates the height of the graph legend in ex units. TODO: This is
        # not accurate! Especially when the font size is changed this does not
        # lead to correct results. But this is a more generic problem of the
        # _HTML_SIZE_PER_EX which is hard coded instead of relying on the font
        # as it should.
        estimated_legend_height_ex = int(
            3.0
            + (
                len(list(artwork_or_errors.artwork.curves))
                + len(artwork_or_errors.artwork.horizontal_rules)
            )
            * 1.5
        )
        # Give the legend at most a third of the available height and ensure
        # the graph keeps at least _MIN_WIDGET_HEIGHT_EX. When the legend
        # exceeds the budget, its container becomes scrollable.
        max_legend_height_ex = min(height // 3, max(height - _MIN_WIDGET_HEIGHT_EX, 0))
        legend_height_ex = min(estimated_legend_height_ex, max_legend_height_ex)
        height -= legend_height_ex
        display_config = display_config.model_copy(
            update={"legend_max_height_px": int(legend_height_ex * _HTML_SIZE_PER_EX)}
        )

    effective_time_range = recipe_with_overrides.time_range or graph_time_range
    interaction = GraphInteractionState(
        consolidation_function=recipe_with_overrides.consolidation_function,
        time_start=effective_time_range.start,
        time_end=effective_time_range.end,
        step=effective_time_range.step,
        value_min=(
            effective_time_range.vertical_range[0] if effective_time_range.vertical_range else None
        ),
        value_max=(
            effective_time_range.vertical_range[1] if effective_time_range.vertical_range else None
        ),
        size_x=width,
        size_y=height,
    )
    return _render_graph_content_html(
        request,
        GraphRenderState(
            interaction=interaction,
            recipe=recipe_with_overrides.recipe,
            specification=recipe_with_overrides.specification,
            display_config=display_config.update_from_options(recipe_with_overrides.render_options),
            display_id=display_id,
        ),
        artwork_or_errors,
        debug=debug,
        graph_timeranges=graph_timeranges,
        temperature_unit=temperature_unit,
        backend_time_series_fetcher=backend_time_series_fetcher,
        expandable_legend_appearance=ExpandableLegendAppearance.POP_UP,
        show_limits_if_reached=True,
    )

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from typing import Final

from tzlocal import get_localzone_name

from cmk.graphing_engine import (
    Graph,
    Unit,
)
from cmk.graphing_engine import HostName as EngineHostName
from cmk.graphing_engine import ServiceName as EngineServiceName
from cmk.gui.config import active_config
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.logged_in import user
from cmk.gui.type_defs import GraphTimerange, PainterParameters, VerticalAxisWidth
from cmk.shared_typing.cmk_time_series_graph import (
    AddTo,
    CmkTimeSeriesGraph,
    ExplicitRange,
    GraphHeader,
    GraphOptions,
    Interaction,
    Size,
    UnitFormat,
    XAxis,
    YAxis,
)
from cmk.shared_typing.global_time_picker import (
    CustomGraphTimeRange,
    FirstDayOfWeek,
    GlobalTimePickerProps,
    GlobalTimePickerRefresh,
)
from cmk.web.utils.html import HTML

from . import _engine_plugins as engine_plugins
from ._engine_discovery import BuiltGraph
from ._engine_dispatch import serialize_graphs
from ._engine_source import RRDFetchMetricNames
from ._engine_template_graphs import build_template_graphs
from ._engine_unit_format import unit_to_unit_format
from ._graph_display_config import HTML_SIZE_PER_EX
from ._graph_specification import GraphSpecification
from ._graph_templates import TemplateGraphSpecification

# A view carrying one of these is driven by the global time picker rather than the
# pnp_timerange painter option, and must not auto-reload.
ENGINE_GRAPH_PAINTER_IDENTS: Final = frozenset(
    {"svc_pnpgraph", "service_graphs", "host_pnpgraph", "host_graphs"}
)


def renders_engine_graphs(painter_idents: Iterable[str]) -> bool:
    """Whether any of the given painters renders through the graph engine."""
    return any(ident in ENGINE_GRAPH_PAINTER_IDENTS for ident in painter_idents)


def stored_time_range_seconds(
    *, painter_parameters: PainterParameters | None, stored_by_the_view: bool
) -> int | None:
    """The "Set default time range" a view stores for a graph painter, `None` for none.
    `Cell.painter_parameters` substitutes the valuespec default when the view stores none, and
    that Dictionary carries the key for every view - hence `stored_by_the_view`."""
    if not stored_by_the_view or painter_parameters is None:
        return None
    return painter_parameters.get("set_default_time_range")


def resolve_default_time_range_seconds(
    graph_timeranges: Sequence[GraphTimerange], preferred_duration: int | None
) -> int:
    """The preferred duration wins as long as it references a configured graph time range;
    otherwise (no or stale preference) the first graph time range definition applies."""
    if preferred_duration is not None and any(
        timerange["duration"] == preferred_duration for timerange in graph_timeranges
    ):
        return preferred_duration
    return graph_timeranges[0]["duration"]


def default_time_range_seconds() -> int:
    """Graph time range shown by default: resolves to the user's preferred graph time range or the
    first of the global settings' graph time range definitions. With builtin time ranges and no
    user preference this resolves to "Last 1 h".
    Keeps graph rendering and global time picker in sync.

    Must be called per-request (not cached at import time) as active_config is only bound within a
    request context.
    """
    return resolve_default_time_range_seconds(
        active_config.graph_timeranges, user.get_attribute("graph_default_time_range")
    )


def user_first_day_of_week() -> FirstDayOfWeek | None:
    """The start of week the global time picker's calendar opens on, None leaving that to the
    browser locale. No preference stored means Monday, not the locale."""
    match user.get_attribute("start_of_week"):
        case "browser_locale":
            return None
        case str() as value:
            try:
                return FirstDayOfWeek(value)
            except ValueError:  # defensive: stale stored value
                return FirstDayOfWeek.monday
        case _:
            return FirstDayOfWeek.monday


def user_default_refresh_time() -> int | None:
    """The user's preferred refresh interval preselected in the global time picker's refresh
    control. None means no preference, in which case the frontend default applies."""
    match user.get_attribute("graph_default_refresh_time"):
        case int() as value:
            return value
        case _:
            return None


_DEFAULT_INTERACTION = Interaction(
    burger="enabled",
    zoom="enabled",
    panning="enabled",
    hover="enabled",
    brush="enabled",
    pin="enabled",
)

# Mobile has no room for the controls and no pointer to drive them with.
STATIC_INTERACTION = Interaction(
    burger="disabled",
    zoom="disabled",
    panning="disabled",
    hover="disabled",
    brush="disabled",
    pin="disabled",
)


def _add_to(specification: GraphSpecification | None, internal: str) -> AddTo | None:
    # A graph offers an add-to action exactly if its specification declares an add-to type: the type
    # is what the context menu is assembled for, the specification is what most actions replay, and
    # the built graph is what a custom graph stores instead of replaying anything.
    if specification is None or (add_type := specification.add_visual_type()) is None:
        return None
    return AddTo(type=add_type, specification=specification.model_dump(), internal=internal)


def unit_from_curves(units: Iterable[Unit]) -> UnitFormat | None:
    """The axis unit taken from the first of an ordered sequence of curve units.

    Every curve in a graph draws in one shared unit (enforced backend-side), so the axis unit is
    the unit of any curve; None when there are no units at all, in which case the renderer falls
    back to raw, unit-less ticks. Shared by derive_y_axis_unit (the pre-evaluation Graph, here) and
    _graph_png._derived_y_axis_unit (the EvaluatedGraph), which carries the same CurveAttributes.unit
    on its curves but has no common curve type to walk with this one.
    """
    return next((unit_to_unit_format(unit) for unit in units), None)


def derive_y_axis_unit(graph: Graph) -> UnitFormat | None:
    """Derive the value axis unit from the graph's own curves.

    Mirrors yAxis.ts:deriveYAxis - template, single-timeseries and combined graphs draw every
    curve in one unit (enforced backend-side), so the axis unit is the unit of any curve. None
    when the graph has no curves; the renderer then falls back to raw, unit-less ticks.
    """
    return unit_from_curves(
        member.attributes.unit for stack in graph.stacks for member in stack.members
    ) or unit_from_curves(line.curve.attributes.unit for line in graph.lines)


def _shell_y_axis(built: BuiltGraph) -> YAxis | None:
    """The axis the shell draws with: what the graph names for itself, else what its curves imply."""
    unit = built.y_axis_unit if built.y_axis_unit is not None else derive_y_axis_unit(built.graph)
    bounds = built.y_axis_bounds()
    if unit is None and bounds is None:
        return None
    return YAxis(
        unit=unit,
        explicit_range=None if bounds is None else ExplicitRange(min=bounds[0], max=bounds[1]),
    )


def to_cmk_time_series_graph(
    built: BuiltGraph,
    *,
    size: Size,
    interaction: Interaction = _DEFAULT_INTERACTION,
    font_size_pt: float = 8.0,
    show_graph_time: bool = True,
    x_axis: XAxis | None = None,
) -> CmkTimeSeriesGraph:
    """Translate a built graph into the shared ``CmkTimeSeriesGraph`` the Vue renderer takes."""
    graph = built.graph
    internal = json.dumps(serialize_graphs([graph]))
    return CmkTimeSeriesGraph(
        size=size,
        options=GraphOptions(
            header=GraphHeader(title=graph.title, show_graph_time=show_graph_time),
            name=graph.name,
            x_axis=x_axis,
            y_axis=_shell_y_axis(built),
            font_size_pt=font_size_pt,
        ),
        interaction=interaction,
        internal=internal,
        add_to=_add_to(built.specification, internal),
    )


def global_time_picker_refresh(
    *,
    interval_seconds: int | None = None,
    starts_live: bool = False,
    reloads_page_content: bool = False,
) -> GlobalTimePickerRefresh:
    return GlobalTimePickerRefresh(
        interval_seconds=interval_seconds or user_default_refresh_time(),
        starts_live=starts_live,
        reloads_page_content=reloads_page_content,
    )


def global_time_picker_props(
    graph_timeranges: Sequence[GraphTimerange],
    default_time_range_seconds: int,
    *,
    first_day_of_week: FirstDayOfWeek | None,
    refresh: GlobalTimePickerRefresh,
) -> GlobalTimePickerProps:
    return GlobalTimePickerProps(
        custom_time_ranges=[
            CustomGraphTimeRange(title=timerange["title"], total_seconds=timerange["duration"])
            for timerange in graph_timeranges
        ],
        default_time_range=default_time_range_seconds,
        server_time_zone=get_localzone_name(),
        first_day_of_week=first_day_of_week,
        refresh=refresh,
    )


def render_global_time_picker(
    graph_timeranges: Sequence[GraphTimerange],
    default_time_range_seconds: int,
    *,
    refresh: GlobalTimePickerRefresh,
) -> None:
    """Render the global time picker frontend component."""
    props = global_time_picker_props(
        graph_timeranges,
        default_time_range_seconds,
        first_day_of_week=user_first_day_of_week(),
        refresh=refresh,
    )
    html.vue_component("cmk-global-time-picker", data=asdict(props))


def value_axis_width_px(
    vertical_axis_width: VerticalAxisWidth,
) -> float | None:
    """None for "fixed": that choice reads "relative to the font size", and a page which offers
    no font size has nothing to be relative to, so the renderer's own default width stands."""
    if isinstance(vertical_axis_width, tuple):
        return vertical_axis_width[1] * 96 / 72
    return None


@dataclass(frozen=True)
class EngineDisplayOptions:
    """What a graph group applies to every graph it renders.

    The component takes these as one ``display`` prop, so a builder either omits it and gets
    every default, or sends the whole object - a partial one would read as "hide" for the keys
    it leaves out.
    """

    show_consolidation: bool = True
    show_legend: bool = True
    show_title: bool = True
    show_vertical_axis: bool = True
    show_time_axis: bool = True
    vertical_axis_width: VerticalAxisWidth = "fixed"

    def as_props(self) -> dict[str, object]:
        props: dict[str, object] = {
            "show_consolidation": self.show_consolidation,
            "show_legend": self.show_legend,
            "show_title": self.show_title,
            "show_vertical_axis": self.show_vertical_axis,
            "show_time_axis": self.show_time_axis,
        }
        # The renderer treats the width as a floor, not an absolute: it still grows to hold the
        # widest label. Absent leaves its own default - see value_axis_width_px.
        if (width := value_axis_width_px(self.vertical_axis_width)) is not None:
            props["min_value_axis_width"] = width
        return props


def render_engine_graph_group(
    specification: TemplateGraphSpecification,
    *,
    host_name: str,
    service_name: str,
    size: Size,
    time_range: tuple[int, int],
    show_graph_time: bool,
    debug: bool,
    display: EngineDisplayOptions = EngineDisplayOptions(),
    interaction: Interaction = _DEFAULT_INTERACTION,
    multi_column: bool = False,
    full_width: bool = False,
) -> HTML:
    """Render the graph-engine (Vue) 'cmk-graph-group' for a host/service's template graphs.

    The metric names are resolved server-side (a single livestatus query); the series
    themselves are fetched client-side by the mounted component.
    """
    engine_graphs = build_template_graphs(
        specification,
        registered_graphs=engine_plugins.registered_graphs(),
        registered_metrics=engine_plugins.registered_metrics(),
        fetch_metric_names=RRDFetchMetricNames(
            host_name=EngineHostName(host_name),
            service_name=EngineServiceName(service_name),
            debug=debug,
            site_id=specification.site,
            registered_translations=engine_plugins.registered_translations(),
        ),
    )
    vue_graphs = [
        asdict(
            to_cmk_time_series_graph(
                built,
                size=size,
                interaction=interaction,
                show_graph_time=show_graph_time,
            )
        )
        for built in engine_graphs
    ]
    # The Size is in ex units; the group's figure is laid out in CSS pixels.
    data: dict[str, object] = {
        "initial_time_range_start": time_range[0],
        "initial_time_range_end": time_range[1],
        "figure_height": int(size.height * HTML_SIZE_PER_EX),
        "graphs": vue_graphs,
        "display": display.as_props(),
        # Only the hover preview flows its many graphs into columns; everywhere else stacks.
        "layout": "wrap" if multi_column else "column",
    }
    # Full-width groups omit figure_width entirely so the component measures the available width
    # itself; only a fixed-size embed (e.g. the hover popup) sends a concrete pixel width.
    if not full_width:
        data["figure_width"] = int(size.width * HTML_SIZE_PER_EX)
    return HTMLWriter.render_vue_component("cmk-graph-group", data)

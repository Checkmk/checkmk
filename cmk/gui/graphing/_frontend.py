#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict
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
from cmk.gui.type_defs import GraphTimerange
from cmk.shared_typing.cmk_time_series_graph import (
    AddTo,
    CmkTimeSeriesGraph,
    GraphHeader,
    GraphOptions,
    Interaction,
    Precision,
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
from ._engine_dispatch import serialize_graphs
from ._engine_source import RRDFetchMetricNames
from ._engine_template_graphs import build_template_graphs
from ._engine_unit_format import notation_name, precision_kind
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
    """The user's preferred start of week in the global time picker's calendar, None meaning the
    browser locale decides."""
    match user.get_attribute("start_of_week"):
        case str() as value:
            try:
                return FirstDayOfWeek(value)
            except ValueError:  # defensive: stale stored value
                return None
        case _:
            return None


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


def unit_to_unit_format(unit: Unit) -> UnitFormat:
    """Translate an engine ``Unit`` into the shared ``UnitFormat`` the Vue graph already speaks."""
    return UnitFormat(
        notation=notation_name(unit),
        symbol=unit.notation.symbol,
        precision=Precision(type=precision_kind(unit), digits=unit.precision.digits),
    )


def y_axis_from_units(units: Iterable[Unit]) -> YAxis | None:
    """The Y-axis derived from the first of an ordered sequence of curve units.

    Every curve in a graph draws in one shared unit (enforced backend-side), so the axis unit is
    the unit of any curve; None when there are no units at all, in which case the renderer falls
    back to raw, unit-less ticks. Shared by derive_y_axis (the pre-evaluation Graph, here) and
    _graph_png._derive_y_axis (the EvaluatedGraph), which carries the same CurveAttributes.unit
    on its curves but has no common curve type to walk with this one.
    """
    return next((YAxis(unit=unit_to_unit_format(unit)) for unit in units), None)


def derive_y_axis(graph: Graph) -> YAxis | None:
    """Derive the Y-axis (its unit) from the graph's own curves.

    Mirrors yAxis.ts:deriveYAxis - template, single-timeseries and combined graphs draw every
    curve in one unit (enforced backend-side), so the axis unit is the unit of any curve. None
    when the graph has no curves; the renderer then falls back to raw, unit-less ticks.
    """
    return y_axis_from_units(
        member.attributes.unit for stack in graph.stacks for member in stack.members
    ) or y_axis_from_units(line.curve.attributes.unit for line in graph.lines)


def to_cmk_time_series_graph(
    graph: Graph,
    *,
    size: Size,
    interaction: Interaction = _DEFAULT_INTERACTION,
    font_size_pt: float = 8.0,
    show_graph_time: bool = True,
    x_axis: XAxis | None = None,
    y_axis: YAxis | None = None,
    add_to_specification: GraphSpecification | None = None,
) -> CmkTimeSeriesGraph:
    """Translate an engine graph definition into the shared ``CmkTimeSeriesGraph``.

    ``y_axis`` defaults to ``derive_y_axis(graph)`` so every caller - the Vue graph group and
    the PNG renderer alike - gets the same server-derived axis without re-deriving it.
    """
    internal = json.dumps(serialize_graphs([graph]))
    return CmkTimeSeriesGraph(
        size=size,
        options=GraphOptions(
            header=GraphHeader(title=graph.title, show_graph_time=show_graph_time),
            name=graph.name,
            x_axis=x_axis,
            y_axis=y_axis if y_axis is not None else derive_y_axis(graph),
            font_size_pt=font_size_pt,
        ),
        interaction=interaction,
        internal=internal,
        add_to=_add_to(add_to_specification, internal),
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


def render_engine_graph_group(
    specification: TemplateGraphSpecification,
    *,
    host_name: str,
    service_name: str,
    size: Size,
    time_range: tuple[int, int],
    show_graph_time: bool,
    debug: bool,
    show_consolidation: bool = True,
    show_legend: bool = True,
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
                built.graph,
                size=size,
                interaction=interaction,
                show_graph_time=show_graph_time,
                add_to_specification=built.specification,
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
        "show_consolidation": show_consolidation,
        "show_legend": show_legend,
        # Only the hover preview flows its many graphs into columns; everywhere else stacks.
        "layout": "wrap" if multi_column else "column",
    }
    # Full-width groups omit figure_width entirely so the component measures the available width
    # itself; only a fixed-size embed (e.g. the hover popup) sends a concrete pixel width.
    if not full_width:
        data["figure_width"] = int(size.width * HTML_SIZE_PER_EX)
    return HTMLWriter.render_vue_component("cmk-graph-group", data)

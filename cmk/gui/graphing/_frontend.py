#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict
from typing import Final

from tzlocal import get_localzone_name

from cmk.graphing_engine import Graph
from cmk.gui.config import active_config
from cmk.gui.htmllib.html import html
from cmk.gui.type_defs import GraphTimerange
from cmk.shared_typing.cmk_time_series_graph import (
    AddTo,
    CmkTimeSeriesGraph,
    GraphHeader,
    GraphOptions,
    Interaction,
    Size,
    XAxis,
    YAxis,
)
from cmk.shared_typing.global_time_picker import CustomGraphTimeRange, GlobalTimePickerProps

from ._engine_dispatch import serialize_graphs
from ._graph_specification import GraphSpecification

# A view carrying one of these is driven by the global time picker rather than the
# pnp_timerange painter option, and must not auto-reload.
ENGINE_GRAPH_PAINTER_IDENTS: Final = frozenset({"svc_pnpgraph"})


def renders_engine_graphs(painter_idents: Iterable[str]) -> bool:
    """Whether any of the given painters renders through the graph engine."""
    return any(ident in ENGINE_GRAPH_PAINTER_IDENTS for ident in painter_idents)


def default_time_range_seconds() -> int:
    """Graph time range shown by default: resolves to the first of the global settings' graph time
    range definitions. With builtin time ranges this resolves to "Last 1 h".
    Keeps graph rendering and global time picker in sync.

    Must be called per-request (not cached at import time) as active_config is only bound within a
    request context.
    """
    return active_config.graph_timeranges[0]["duration"]


_DEFAULT_INTERACTION = Interaction(
    burger="enabled",
    zoom="enabled",
    panning="enabled",
    hover="enabled",
)


def _add_to(specification: GraphSpecification | None) -> AddTo | None:
    # A graph offers an add-to action exactly if its specification declares an add-to type: the type
    # is what the context menu is assembled for, the specification is what the actions replay.
    if specification is None or (add_type := specification.add_visual_type()) is None:
        return None
    return AddTo(type=add_type, specification=specification.model_dump())


def to_cmk_time_series_graph(
    graph: Graph,
    *,
    size: Size,
    interaction: Interaction = _DEFAULT_INTERACTION,
    show_pin: bool = True,
    font_size_pt: float = 8.0,
    show_graph_time: bool = True,
    x_axis: XAxis | None = None,
    y_axis: YAxis | None = None,
    add_to_specification: GraphSpecification | None = None,
) -> CmkTimeSeriesGraph:
    """Translate an engine graph definition into the shared ``CmkTimeSeriesGraph``."""
    return CmkTimeSeriesGraph(
        size=size,
        options=GraphOptions(
            header=GraphHeader(title=graph.title, show_graph_time=show_graph_time),
            name=graph.name,
            x_axis=x_axis,
            y_axis=y_axis,
            show_pin=show_pin,
            font_size_pt=font_size_pt,
        ),
        interaction=interaction,
        internal=json.dumps(serialize_graphs([graph])),
        add_to=_add_to(add_to_specification),
    )


def global_time_picker_props(
    graph_timeranges: Sequence[GraphTimerange],
    default_time_range_seconds: int,
) -> GlobalTimePickerProps:
    """Assemble the global time picker props from the configured graph time ranges."""
    return GlobalTimePickerProps(
        custom_time_ranges=[
            CustomGraphTimeRange(title=timerange["title"], total_seconds=timerange["duration"])
            for timerange in graph_timeranges
        ],
        default_time_range=default_time_range_seconds,
        server_time_zone=get_localzone_name(),
    )


def render_global_time_picker(
    graph_timeranges: Sequence[GraphTimerange],
    default_time_range_seconds: int,
) -> None:
    """Render the global time picker frontend component."""
    props = global_time_picker_props(graph_timeranges, default_time_range_seconds)
    html.vue_component("cmk-global-time-picker", data=asdict(props))

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence
from dataclasses import asdict

from tzlocal import get_localzone_name

from cmk.graphing_engine import Graph
from cmk.gui.htmllib.html import html
from cmk.gui.type_defs import GraphTimerange
from cmk.shared_typing.cmk_time_series_graph import (
    CmkTimeSeriesGraph,
    GraphHeader,
    GraphOptions,
    Interaction,
    Size,
    XAxis,
    YAxis,
)
from cmk.shared_typing.global_time_picker import CustomGraphTimeRange, GlobalTimePickerProps

from ._engine_serialization import serialize_graphs

_DEFAULT_INTERACTION = Interaction(
    burger="enabled",
    zoom="enabled",
    panning="enabled",
    hover="enabled",
)


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
        graph_type=graph.graph_type,
        internal=json.dumps(serialize_graphs([graph])),
    )


def render_global_time_picker(
    graph_timeranges: Sequence[GraphTimerange],
    default_time_range_seconds: int,
) -> None:
    """Render the global time picker frontend component."""
    props = GlobalTimePickerProps(
        custom_time_ranges=[
            CustomGraphTimeRange(title=timerange["title"], total_seconds=timerange["duration"])
            for timerange in graph_timeranges
        ],
        default_time_range=default_time_range_seconds,
        server_time_zone=get_localzone_name(),
    )
    html.vue_component("cmk-global-time-picker", data=asdict(props))

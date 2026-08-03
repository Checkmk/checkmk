#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Render the engine-based (Vue) 'cmk-graph-group' for a host/service's template graphs."""

from dataclasses import asdict

from cmk.graphing_engine import HostName as EngineHostName
from cmk.graphing_engine import ServiceName as EngineServiceName
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.utils.html import HTML
from cmk.shared_typing.cmk_time_series_graph import Interaction, Size

from . import _engine_plugins as engine_plugins
from ._engine_rrd import EngineRRDFetchMetricNames
from ._engine_template_graphs import build_template_graphs
from ._frontend import _DEFAULT_INTERACTION, to_cmk_time_series_graph
from ._graph_display_config import HTML_SIZE_PER_EX
from ._graph_templates import TemplateGraphSpecification


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
) -> HTML:
    """Render the graph-engine (Vue) 'cmk-graph-group' for a host/service's template graphs.

    The metric names are resolved server-side (a single livestatus query); the series
    themselves are fetched client-side by the mounted component.
    """
    engine_graphs = build_template_graphs(
        specification,
        registered_graphs=engine_plugins.registered_graphs(),
        registered_metrics=engine_plugins.registered_metrics(),
        fetch_metric_names=EngineRRDFetchMetricNames(
            host_name=EngineHostName(host_name),
            service_name=EngineServiceName(service_name),
            debug=debug,
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
        "figure_width": int(size.width * HTML_SIZE_PER_EX),
        "figure_height": int(size.height * HTML_SIZE_PER_EX),
        "graphs": vue_graphs,
        "show_consolidation": show_consolidation,
        "show_legend": show_legend,
    }
    return HTMLWriter.render_vue_component("cmk-graph-group", data)

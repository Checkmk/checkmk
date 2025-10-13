#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_requests_cmk_views = metrics.Metric(
    name="requests_cmk_views",
    title=Title("Checkmk: Views: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_RED,
)
metric_requests_cmk_wato = metrics.Metric(
    name="requests_cmk_wato",
    title=Title("Checkmk: Setup: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
metric_requests_cmk_bi = metrics.Metric(
    name="requests_cmk_bi",
    title=Title("Checkmk: BI: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_requests_cmk_snapins = metrics.Metric(
    name="requests_cmk_snapins",
    title=Title("Checkmk: Sidebar elements: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.RED,
)
metric_requests_cmk_dashboards = metrics.Metric(
    name="requests_cmk_dashboards",
    title=Title("Checkmk: Dashboards: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_requests_cmk_api = metrics.Metric(
    name="requests_cmk_api",
    title=Title("Checkmk: API: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_requests_cmk_ajax = metrics.Metric(
    name="requests_cmk_ajax",
    title=Title("Checkmk: Ajax: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_YELLOW,
)
metric_requests_cmk_index = metrics.Metric(
    name="requests_cmk_index",
    title=Title("Checkmk: Index: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)
metric_requests_cmk_login = metrics.Metric(
    name="requests_cmk_login",
    title=Title("Checkmk: Login: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_RED,
)
metric_requests_cmk_search = metrics.Metric(
    name="requests_cmk_search",
    title=Title("Checkmk: Search: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BROWN,
)
metric_requests_cmk_sidebar = metrics.Metric(
    name="requests_cmk_sidebar",
    title=Title("Checkmk: Sidebar: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BROWN,
)
metric_requests_cmk_graphs = metrics.Metric(
    name="requests_cmk_graphs",
    title=Title("Checkmk: Graphs: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BROWN,
)
metric_requests_cmk_other = metrics.Metric(
    name="requests_cmk_other",
    title=Title("Checkmk: Other: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_requests_nagvis_snapin = metrics.Metric(
    name="requests_nagvis_snapin",
    title=Title("NagVis: Sidebar element: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_requests_nagvis_ajax = metrics.Metric(
    name="requests_nagvis_ajax",
    title=Title("NagVis: AJAX: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_PURPLE,
)
metric_requests_nagvis_other = metrics.Metric(
    name="requests_nagvis_other",
    title=Title("NagVis: Other: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_requests_images = metrics.Metric(
    name="requests_images",
    title=Title("Image: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_requests_styles = metrics.Metric(
    name="requests_styles",
    title=Title("Styles: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_requests_scripts = metrics.Metric(
    name="requests_scripts",
    title=Title("Scripts: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_requests_other = metrics.Metric(
    name="requests_other",
    title=Title("Other: Requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)

graph_handled_requests = graphs.Graph(
    name="handled_requests",
    title=Title("Handled Requests"),
    compound_lines=[
        "requests_cmk_views",
        "requests_cmk_wato",
        "requests_cmk_bi",
        "requests_cmk_snapins",
        "requests_cmk_dashboards",
        "requests_cmk_api",
        "requests_cmk_ajax",
        "requests_cmk_index",
        "requests_cmk_login",
        "requests_cmk_search",
        "requests_cmk_sidebar",
        "requests_cmk_graphs",
        "requests_cmk_other",
        "requests_nagvis_snapin",
        "requests_nagvis_ajax",
        "requests_nagvis_other",
        "requests_images",
        "requests_styles",
        "requests_scripts",
        "requests_other",
    ],
)

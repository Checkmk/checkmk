#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))

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

metric_bytes_cmk_views = metrics.Metric(
    name="bytes_cmk_views",
    title=Title("Checkmk: Views: Bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_RED,
)

metric_bytes_cmk_wato = metrics.Metric(
    name="bytes_cmk_wato",
    title=Title("Checkmk: Setup: Bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)

metric_bytes_cmk_bi = metrics.Metric(
    name="bytes_cmk_bi",
    title=Title("Checkmk: BI: Bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)

metric_bytes_cmk_snapins = metrics.Metric(
    name="bytes_cmk_snapins",
    title=Title("Checkmk: Sidebar elements: Bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.RED,
)

metric_bytes_cmk_dashboards = metrics.Metric(
    name="bytes_cmk_dashboards",
    title=Title("Checkmk: Dashboards: Bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)

metric_bytes_cmk_other = metrics.Metric(
    name="bytes_cmk_other",
    title=Title("Checkmk: Other: Bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_bytes_nagvis_snapin = metrics.Metric(
    name="bytes_nagvis_snapin",
    title=Title("NagVis: Sidebar element: Bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_ORANGE,
)

metric_bytes_nagvis_ajax = metrics.Metric(
    name="bytes_nagvis_ajax",
    title=Title("NagVis: AJAX: Bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_bytes_nagvis_other = metrics.Metric(
    name="bytes_nagvis_other",
    title=Title("NagVis: Other: Bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_bytes_images = metrics.Metric(
    name="bytes_images",
    title=Title("Image: Bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_bytes_styles = metrics.Metric(
    name="bytes_styles",
    title=Title("Styles: Bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)

metric_bytes_scripts = metrics.Metric(
    name="bytes_scripts",
    title=Title("Scripts: Bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.GREEN,
)

metric_bytes_other = metrics.Metric(
    name="bytes_other",
    title=Title("Other: Bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)

metric_secs_cmk_views = metrics.Metric(
    name="secs_cmk_views",
    title=Title("Checkmk: Views: Secs"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_RED,
)

metric_secs_cmk_wato = metrics.Metric(
    name="secs_cmk_wato",
    title=Title("Checkmk: Setup: Secs"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)

metric_secs_cmk_bi = metrics.Metric(
    name="secs_cmk_bi",
    title=Title("Checkmk: BI: Secs"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

metric_secs_cmk_snapins = metrics.Metric(
    name="secs_cmk_snapins",
    title=Title("Checkmk: Sidebar elements: Secs"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.RED,
)

metric_secs_cmk_dashboards = metrics.Metric(
    name="secs_cmk_dashboards",
    title=Title("Checkmk: Dashboards: Secs"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)

metric_secs_cmk_other = metrics.Metric(
    name="secs_cmk_other",
    title=Title("Checkmk: Other: Secs"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_secs_nagvis_snapin = metrics.Metric(
    name="secs_nagvis_snapin",
    title=Title("NagVis: Sidebar element: Secs"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_ORANGE,
)

metric_secs_nagvis_ajax = metrics.Metric(
    name="secs_nagvis_ajax",
    title=Title("NagVis: AJAX: Secs"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_secs_nagvis_other = metrics.Metric(
    name="secs_nagvis_other",
    title=Title("NagVis: Other: Secs"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_secs_images = metrics.Metric(
    name="secs_images",
    title=Title("Image: Secs"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_secs_styles = metrics.Metric(
    name="secs_styles",
    title=Title("Styles: Secs"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)

metric_secs_scripts = metrics.Metric(
    name="secs_scripts",
    title=Title("Scripts: Secs"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

metric_secs_other = metrics.Metric(
    name="secs_other",
    title=Title("Other: Secs"),
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

graph_cmk_http_pagetimes = graphs.Graph(
    name="cmk_http_pagetimes",
    title=Title("Time spent for various page types"),
    compound_lines=[
        "secs_cmk_views",
        "secs_cmk_wato",
        "secs_cmk_bi",
        "secs_cmk_snapins",
        "secs_cmk_dashboards",
        "secs_cmk_other",
        "secs_nagvis_snapin",
        "secs_nagvis_ajax",
        "secs_nagvis_other",
        "secs_images",
        "secs_styles",
        "secs_scripts",
        "secs_other",
    ],
)

graph_cmk_http_traffic = graphs.Graph(
    name="cmk_http_traffic",
    title=Title("Bytes sent"),
    compound_lines=[
        "bytes_cmk_views",
        "bytes_cmk_wato",
        "bytes_cmk_bi",
        "bytes_cmk_snapins",
        "bytes_cmk_dashboards",
        "bytes_cmk_other",
        "bytes_nagvis_snapin",
        "bytes_nagvis_ajax",
        "bytes_nagvis_other",
        "bytes_images",
        "bytes_styles",
        "bytes_scripts",
        "bytes_other",
    ],
)

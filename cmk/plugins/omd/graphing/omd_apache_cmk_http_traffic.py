#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))

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

#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

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

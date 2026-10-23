#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

metric_kube_agent_scrapers = metrics.Metric(
    name="kube_agent_scrapers",
    title=Title("Node-scraper nodes"),
    unit=metrics.Unit(metrics.DecimalNotation("")),
    color=metrics.Color.BLUE,
)

metric_kube_agent_scrapers_affected = metrics.Metric(
    name="kube_agent_scrapers_affected",
    title=Title("Affected node-scraper nodes"),
    unit=metrics.Unit(metrics.DecimalNotation("")),
    color=metrics.Color.RED,
)

graph_kube_agent_scrapers = graphs.Graph(
    name="kube_agent_scrapers",
    title=Title("Node-scraper coverage"),
    simple_lines=[
        "kube_agent_scrapers",
        "kube_agent_scrapers_affected",
    ],
)

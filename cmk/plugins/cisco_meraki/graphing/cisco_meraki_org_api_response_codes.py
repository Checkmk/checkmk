#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from cmk.graphing.v1 import graphs, metrics, Title

metric_api_code_2xx = metrics.Metric(
    name="api_code_2xx",
    title=Title("Code 2xx"),
    unit=metrics.Unit(metrics.DecimalNotation("")),
    color=metrics.Color.LIGHT_GREEN,
)

metric_api_code_3xx = metrics.Metric(
    name="api_code_3xx",
    title=Title("Code 3xx"),
    unit=metrics.Unit(metrics.DecimalNotation("")),
    color=metrics.Color.LIGHT_BLUE,
)

metric_api_code_4xx = metrics.Metric(
    name="api_code_4xx",
    title=Title("Code 4xx"),
    unit=metrics.Unit(metrics.DecimalNotation("")),
    color=metrics.Color.LIGHT_RED,
)

metric_api_code_5xx = metrics.Metric(
    name="api_code_5xx",
    title=Title("Code 5xx"),
    unit=metrics.Unit(metrics.DecimalNotation("")),
    color=metrics.Color.DARK_RED,
)

graph_cisco_meraki_organisations_api_code = graphs.Bidirectional(
    name="cisco_meraki_organisations_api_code",
    title=Title("Cisco Meraki API response codes"),
    upper=graphs.Graph(
        name="api_code_ok",
        title=Title("Cisco Meraki API response codes"),
        simple_lines=[
            "api_code_2xx",
            "api_code_3xx",
        ],
        optional=[
            "api_code_2xx",
            "api_code_3xx",
        ],
    ),
    lower=graphs.Graph(
        name="api_code_bad",
        title=Title("Cisco Meraki API response codes"),
        simple_lines=[
            "api_code_4xx",
            "api_code_5xx",
        ],
        optional=[
            "api_code_4xx",
            "api_code_5xx",
        ],
    ),
)

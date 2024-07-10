#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_varnish_fetch_1xx_rate = metrics.Metric(
    name="varnish_fetch_1xx_rate",
    title=Title("Fetch no body (1xx)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_varnish_fetch_204_rate = metrics.Metric(
    name="varnish_fetch_204_rate",
    title=Title("Fetch no body (204)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BROWN,
)
metric_varnish_fetch_304_rate = metrics.Metric(
    name="varnish_fetch_304_rate",
    title=Title("Fetch no body (304)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_CYAN,
)
metric_varnish_fetch_bad_rate = metrics.Metric(
    name="varnish_fetch_bad_rate",
    title=Title("Fetch had bad headers"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PURPLE,
)
metric_varnish_fetch_chunked_rate = metrics.Metric(
    name="varnish_fetch_chunked_rate",
    title=Title("Fetch chunked"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BROWN,
)
metric_varnish_fetch_close_rate = metrics.Metric(
    name="varnish_fetch_close_rate",
    title=Title("Fetch wanted close"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_PINK,
)
metric_varnish_fetch_eof_rate = metrics.Metric(
    name="varnish_fetch_eof_rate",
    title=Title("Fetch EOF"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_varnish_fetch_failed_rate = metrics.Metric(
    name="varnish_fetch_failed_rate",
    title=Title("Fetch failed"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_PURPLE,
)
metric_varnish_fetch_head_rate = metrics.Metric(
    name="varnish_fetch_head_rate",
    title=Title("Fetch head"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_GREEN,
)
metric_varnish_fetch_length_rate = metrics.Metric(
    name="varnish_fetch_length_rate",
    title=Title("Fetch with length"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
metric_varnish_fetch_oldhttp_rate = metrics.Metric(
    name="varnish_fetch_oldhttp_rate",
    title=Title("Fetch pre HTTP/1.1 closed"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_varnish_fetch_zero_rate = metrics.Metric(
    name="varnish_fetch_zero_rate",
    title=Title("Fetch zero length"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)

graph_varnish_fetch = graphs.Graph(
    name="varnish_fetch",
    title=Title("Varnish Fetch"),
    simple_lines=[
        "varnish_fetch_oldhttp_rate",
        "varnish_fetch_head_rate",
        "varnish_fetch_eof_rate",
        "varnish_fetch_zero_rate",
        "varnish_fetch_304_rate",
        "varnish_fetch_length_rate",
        "varnish_fetch_failed_rate",
        "varnish_fetch_bad_rate",
        "varnish_fetch_close_rate",
        "varnish_fetch_1xx_rate",
        "varnish_fetch_chunked_rate",
        "varnish_fetch_204_rate",
    ],
)

#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_varnish_backend_busy_rate = metrics.Metric(
    name="varnish_backend_busy_rate",
    title=Title("Backend Conn. too many"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.RED,
)
metric_varnish_backend_conn_rate = metrics.Metric(
    name="varnish_backend_conn_rate",
    title=Title("Backend Conn. success"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_varnish_backend_fail_rate = metrics.Metric(
    name="varnish_backend_fail_rate",
    title=Title("Backend Conn. failures"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_varnish_backend_recycle_rate = metrics.Metric(
    name="varnish_backend_recycle_rate",
    title=Title("Backend Conn. recycles"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_varnish_backend_req_rate = metrics.Metric(
    name="varnish_backend_req_rate",
    title=Title("Backend Conn. requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_varnish_backend_retry_rate = metrics.Metric(
    name="varnish_backend_retry_rate",
    title=Title("Backend Conn. retry"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_varnish_backend_reuse_rate = metrics.Metric(
    name="varnish_backend_reuse_rate",
    title=Title("Backend Conn. reuses"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BROWN,
)
metric_varnish_backend_toolate_rate = metrics.Metric(
    name="varnish_backend_toolate_rate",
    title=Title("Backend Conn. was closed"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_varnish_backend_unhealthy_rate = metrics.Metric(
    name="varnish_backend_unhealthy_rate",
    title=Title("Backend Conn. not attempted"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)

graph_varnish_backend_connections = graphs.Graph(
    name="varnish_backend_connections",
    title=Title("Varnish Backend Connections"),
    simple_lines=[
        "varnish_backend_busy_rate",
        "varnish_backend_unhealthy_rate",
        "varnish_backend_req_rate",
        "varnish_backend_recycle_rate",
        "varnish_backend_retry_rate",
        "varnish_backend_fail_rate",
        "varnish_backend_toolate_rate",
        "varnish_backend_conn_rate",
        "varnish_backend_reuse_rate",
    ],
)

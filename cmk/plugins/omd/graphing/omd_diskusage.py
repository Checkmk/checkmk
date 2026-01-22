#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_omd_log_size = metrics.Metric(
    name="omd_log_size",
    title=Title("Size of log files"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_omd_rrd_size = metrics.Metric(
    name="omd_rrd_size",
    title=Title("Size of RRDs"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_PURPLE,
)

metric_omd_pnp4nagios_size = metrics.Metric(
    name="omd_pnp4nagios_size",
    title=Title("Size of PNP4Nagios"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_CYAN,
)

metric_omd_tmp_size = metrics.Metric(
    name="omd_tmp_size",
    title=Title("Size of tmp"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_CYAN,
)

metric_omd_local_size = metrics.Metric(
    name="omd_local_size",
    title=Title("Size of local"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_PINK,
)

metric_omd_agents_size = metrics.Metric(
    name="omd_agents_size",
    title=Title("Size of agents"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_PINK,
)

metric_omd_history_size = metrics.Metric(
    name="omd_history_size",
    title=Title("Size of history"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_GREEN,
)

metric_omd_core_size = metrics.Metric(
    name="omd_core_size",
    title=Title("Size of core"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_GREEN,
)

metric_omd_inventory_size = metrics.Metric(
    name="omd_inventory_size",
    title=Title("Size of inventory"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_BROWN,
)

metric_omd_crashes_size = metrics.Metric(
    name="omd_crashes_size",
    title=Title("Size of crashes"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_ORANGE,
)

metric_omd_size = metrics.Metric(
    name="omd_size",
    title=Title("Total size of site"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_BROWN,
)

metric_omd_otel_collector_size = metrics.Metric(
    name="omd_otel_collector_size",
    title=Title("Size of OTel Collector"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_BLUE,
)

metric_omd_metric_backend_size = metrics.Metric(
    name="omd_metric_backend_size",
    title=Title("Size of metric backend"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_RED,
)


graph_omd_fileusage = graphs.Graph(
    name="omd_fileusage",
    title=Title("OMD filesystem usage"),
    compound_lines=[
        "omd_log_size",
        "omd_rrd_size",
        "omd_pnp4nagios_size",
        "omd_tmp_size",
        "omd_local_size",
        "omd_agents_size",
        "omd_history_size",
        "omd_core_size",
        "omd_inventory_size",
        "omd_crashes_size",
        "omd_otel_collector_size",
        "omd_metric_backend_size",
    ],
    simple_lines=["omd_size"],
    optional=[
        "omd_log_size",
        "omd_rrd_size",
        "omd_pnp4nagios_size",
        "omd_tmp_size",
        "omd_local_size",
        "omd_agents_size",
        "omd_history_size",
        "omd_core_size",
        "omd_inventory_size",
        "omd_crashes_size",
        "omd_metric_backend_size",
    ],
)

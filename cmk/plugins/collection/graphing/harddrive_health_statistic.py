#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_harddrive_cmd_timeouts = metrics.Metric(
    name="harddrive_cmd_timeouts",
    title=Title("Harddrive command timeouts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GRAY,
)
metric_harddrive_end_to_end_errors = metrics.Metric(
    name="harddrive_end_to_end_errors",
    title=Title("Harddrive end-to-end errors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_harddrive_pending_sectors = metrics.Metric(
    name="harddrive_pending_sectors",
    title=Title("Harddrive pending sectors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_harddrive_power_cycles = metrics.Metric(
    name="harddrive_power_cycles",
    title=Title("Harddrive power cycles"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_harddrive_reallocated_events = metrics.Metric(
    name="harddrive_reallocated_events",
    title=Title("Harddrive reallocated events"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_YELLOW,
)
metric_harddrive_reallocated_sectors = metrics.Metric(
    name="harddrive_reallocated_sectors",
    title=Title("Harddrive reallocated sectors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_harddrive_spin_retries = metrics.Metric(
    name="harddrive_spin_retries",
    title=Title("Harddrive spin retries"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_harddrive_udma_crc_errors = metrics.Metric(
    name="harddrive_udma_crc_errors",
    title=Title("Harddrive UDMA CRC errors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PINK,
)
metric_harddrive_uncorrectable_errors = metrics.Metric(
    name="harddrive_uncorrectable_errors",
    title=Title("Harddrive uncorrectable errors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BROWN,
)

graph_harddrive_health_statistic = graphs.Graph(
    name="harddrive_health_statistic",
    title=Title("Harddrive health statistic"),
    compound_lines=[
        "harddrive_power_cycles",
        "harddrive_reallocated_sectors",
        "harddrive_reallocated_events",
        "harddrive_spin_retries",
        "harddrive_pending_sectors",
        "harddrive_cmd_timeouts",
        "harddrive_end_to_end_errors",
        "harddrive_uncorrectable_errors",
        "harddrive_udma_crc_errors",
    ],
)

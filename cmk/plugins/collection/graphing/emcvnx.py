#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_emcvnx_move_down = metrics.Metric(
    name="emcvnx_move_down",
    title=Title("Data to move down"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_emcvnx_move_up = metrics.Metric(
    name="emcvnx_move_up",
    title=Title("Data to move up"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_emcvnx_move_within = metrics.Metric(
    name="emcvnx_move_within",
    title=Title("Data to move within"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_emcvnx_move_completed = metrics.Metric(
    name="emcvnx_move_completed",
    title=Title("Data movement completed"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_emcvnx_avail_capacity = metrics.Metric(
    name="emcvnx_avail_capacity",
    title=Title("Available capacity"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_emcvnx_consumed_capacity = metrics.Metric(
    name="emcvnx_consumed_capacity",
    title=Title("Consumed capacity"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_emcvnx_dedupl_remaining_size = metrics.Metric(
    name="emcvnx_dedupl_remaining_size",
    title=Title("Deduplication remaining size"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_emcvnx_targeted_higher = metrics.Metric(
    name="emcvnx_targeted_higher",
    title=Title("Data targeted for higher tier"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_emcvnx_targeted_lower = metrics.Metric(
    name="emcvnx_targeted_lower",
    title=Title("Data targeted for lower tier"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_emcvnx_targeted_within = metrics.Metric(
    name="emcvnx_targeted_within",
    title=Title("Data targeted for within tier"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_emcvnx_over_subscribed = metrics.Metric(
    name="emcvnx_over_subscribed",
    title=Title("Oversubscribed"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_PINK,
)
metric_emcvnx_total_subscribed_capacity = metrics.Metric(
    name="emcvnx_total_subscribed_capacity",
    title=Title("Total subscribed capacity"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
metric_emcvnx_perc_full = metrics.Metric(
    name="emcvnx_perc_full",
    title=Title("Percent full"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_emcvnx_perc_subscribed = metrics.Metric(
    name="emcvnx_perc_subscribed",
    title=Title("Percent subscribed"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_emcvnx_time_to_complete = metrics.Metric(
    name="emcvnx_time_to_complete",
    title=Title("Estimated time to complete"),
    unit=UNIT_TIME,
    color=metrics.Color.CYAN,
)
metric_emcvnx_dedupl_perc_completed = metrics.Metric(
    name="emcvnx_dedupl_perc_completed",
    title=Title("Deduplication percent completed"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_emcvnx_dedupl_efficiency_savings = metrics.Metric(
    name="emcvnx_dedupl_efficiency_savings",
    title=Title("Deduplication efficiency savings"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_emcvnx_dedupl_shared_capacity = metrics.Metric(
    name="emcvnx_dedupl_shared_capacity",
    title=Title("Deduplication shared capacity"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)

perfometer_emcvnx_move_completed = perfometers.Perfometer(
    name="emcvnx_move_completed",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(500000000000),
    ),
    segments=["emcvnx_move_completed"],
)
perfometer_emcvnx_consumed_capacity = perfometers.Perfometer(
    name="emcvnx_consumed_capacity",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(40000000000000),
    ),
    segments=["emcvnx_consumed_capacity"],
)
perfometer_emcvnx_dedupl_remaining_size = perfometers.Perfometer(
    name="emcvnx_dedupl_remaining_size",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(40000000000000),
    ),
    segments=["emcvnx_dedupl_remaining_size"],
)

graph_emcvnx_storage_pools_movement = graphs.Graph(
    name="emcvnx_storage_pools_movement",
    title=Title("EMC VNX storage pools movement"),
    compound_lines=[
        "emcvnx_move_up",
        "emcvnx_move_down",
        "emcvnx_move_within",
    ],
)
graph_emcvnx_storage_pools_capacity = graphs.Graph(
    name="emcvnx_storage_pools_capacity",
    title=Title("EMC VNX storage pools capacity"),
    compound_lines=[
        "emcvnx_consumed_capacity",
        "emcvnx_avail_capacity",
    ],
)
graph_emcvnx_storage_pools_targeted = graphs.Graph(
    name="emcvnx_storage_pools_targeted",
    title=Title("EMC VNX storage pools targeted tiers"),
    compound_lines=[
        "emcvnx_targeted_higher",
        "emcvnx_targeted_lower",
        "emcvnx_targeted_within",
    ],
)

#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_oracle_wait_class_administrative_waited = metrics.Metric(
    name="oracle_wait_class_administrative_waited",
    title=Title("Oracle administrative wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_RED,
)
metric_oracle_wait_class_administrative_waited_fg = metrics.Metric(
    name="oracle_wait_class_administrative_waited_fg",
    title=Title("Oracle administrative wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_RED,
)
metric_oracle_wait_class_application_waited = metrics.Metric(
    name="oracle_wait_class_application_waited",
    title=Title("Oracle application wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_RED,
)
metric_oracle_wait_class_application_waited_fg = metrics.Metric(
    name="oracle_wait_class_application_waited_fg",
    title=Title("Oracle application wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_RED,
)
metric_oracle_wait_class_cluster_waited = metrics.Metric(
    name="oracle_wait_class_cluster_waited",
    title=Title("Oracle cluster wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_oracle_wait_class_cluster_waited_fg = metrics.Metric(
    name="oracle_wait_class_cluster_waited_fg",
    title=Title("Oracle cluster wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_oracle_wait_class_commit_waited = metrics.Metric(
    name="oracle_wait_class_commit_waited",
    title=Title("Oracle commit wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_wait_class_commit_waited_fg = metrics.Metric(
    name="oracle_wait_class_commit_waited_fg",
    title=Title("Oracle commit wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_wait_class_concurrency_waited = metrics.Metric(
    name="oracle_wait_class_concurrency_waited",
    title=Title("Oracle concurrency wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_oracle_wait_class_concurrency_waited_fg = metrics.Metric(
    name="oracle_wait_class_concurrency_waited_fg",
    title=Title("Oracle concurrency wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_oracle_wait_class_configuration_waited = metrics.Metric(
    name="oracle_wait_class_configuration_waited",
    title=Title("Oracle configuration wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_GREEN,
)
metric_oracle_wait_class_configuration_waited_fg = metrics.Metric(
    name="oracle_wait_class_configuration_waited_fg",
    title=Title("Oracle configuration wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_GREEN,
)
metric_oracle_wait_class_idle_waited = metrics.Metric(
    name="oracle_wait_class_idle_waited",
    title=Title("Oracle idle wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_oracle_wait_class_idle_waited_fg = metrics.Metric(
    name="oracle_wait_class_idle_waited_fg",
    title=Title("Oracle idle wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_oracle_wait_class_network_waited = metrics.Metric(
    name="oracle_wait_class_network_waited",
    title=Title("Oracle network wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_wait_class_network_waited_fg = metrics.Metric(
    name="oracle_wait_class_network_waited_fg",
    title=Title("Oracle network wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_wait_class_other_waited = metrics.Metric(
    name="oracle_wait_class_other_waited",
    title=Title("Oracle other wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_wait_class_other_waited_fg = metrics.Metric(
    name="oracle_wait_class_other_waited_fg",
    title=Title("Oracle other wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_wait_class_scheduler_waited = metrics.Metric(
    name="oracle_wait_class_scheduler_waited",
    title=Title("Oracle scheduler wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_wait_class_scheduler_waited_fg = metrics.Metric(
    name="oracle_wait_class_scheduler_waited_fg",
    title=Title("Oracle scheduler wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_wait_class_system_io_waited = metrics.Metric(
    name="oracle_wait_class_system_io_waited",
    title=Title("Oracle system I/O wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_oracle_wait_class_system_io_waited_fg = metrics.Metric(
    name="oracle_wait_class_system_io_waited_fg",
    title=Title("Oracle system I/O wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_oracle_wait_class_total = metrics.Metric(
    name="oracle_wait_class_total",
    title=Title("Oracle total waited"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLACK,
)
metric_oracle_wait_class_total_fg = metrics.Metric(
    name="oracle_wait_class_total_fg",
    title=Title("Oracle total waited (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLACK,
)
metric_oracle_wait_class_user_io_waited = metrics.Metric(
    name="oracle_wait_class_user_io_waited",
    title=Title("Oracle user I/O wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BROWN,
)
metric_oracle_wait_class_user_io_waited_fg = metrics.Metric(
    name="oracle_wait_class_user_io_waited_fg",
    title=Title("Oracle user I/O wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BROWN,
)

perfometer_oracle_wait_class_total = perfometers.Bidirectional(
    name="oracle_wait_class_total",
    left=perfometers.Perfometer(
        name="oracle_wait_class_total",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(90),
        ),
        segments=["oracle_wait_class_total"],
    ),
    right=perfometers.Perfometer(
        name="oracle_wait_class_total_fg",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(90),
        ),
        segments=["oracle_wait_class_total_fg"],
    ),
)

graph_oracle_wait_class = graphs.Bidirectional(
    name="oracle_wait_class",
    title=Title("Oracle Wait Class (FG lines are downside)"),
    lower=graphs.Graph(
        name="oracle_wait_class_fg",
        title=Title("Oracle wait class"),
        simple_lines=[
            "oracle_wait_class_total_fg",
            "oracle_wait_class_administrative_waited_fg",
            "oracle_wait_class_application_waited_fg",
            "oracle_wait_class_cluster_waited_fg",
            "oracle_wait_class_commit_waited_fg",
            "oracle_wait_class_concurrency_waited_fg",
            "oracle_wait_class_configuration_waited_fg",
            "oracle_wait_class_idle_waited_fg",
            "oracle_wait_class_network_waited_fg",
            "oracle_wait_class_other_waited_fg",
            "oracle_wait_class_scheduler_waited_fg",
            "oracle_wait_class_system_io_waited_fg",
            "oracle_wait_class_user_io_waited_fg",
        ],
        optional=[
            "oracle_wait_class_administrative_waited_fg",
            "oracle_wait_class_application_waited_fg",
            "oracle_wait_class_cluster_waited_fg",
            "oracle_wait_class_commit_waited_fg",
            "oracle_wait_class_concurrency_waited_fg",
            "oracle_wait_class_configuration_waited_fg",
            "oracle_wait_class_idle_waited_fg",
            "oracle_wait_class_network_waited_fg",
            "oracle_wait_class_other_waited_fg",
            "oracle_wait_class_scheduler_waited_fg",
            "oracle_wait_class_system_io_waited_fg",
            "oracle_wait_class_user_io_waited_fg",
        ],
    ),
    upper=graphs.Graph(
        name="oracle_wait_class_waited",
        title=Title("Oracle wait class"),
        simple_lines=[
            "oracle_wait_class_total",
            "oracle_wait_class_administrative_waited",
            "oracle_wait_class_application_waited",
            "oracle_wait_class_cluster_waited",
            "oracle_wait_class_commit_waited",
            "oracle_wait_class_concurrency_waited",
            "oracle_wait_class_configuration_waited",
            "oracle_wait_class_idle_waited",
            "oracle_wait_class_network_waited",
            "oracle_wait_class_other_waited",
            "oracle_wait_class_scheduler_waited",
            "oracle_wait_class_system_io_waited",
            "oracle_wait_class_user_io_waited",
        ],
        optional=[
            "oracle_wait_class_administrative_waited",
            "oracle_wait_class_application_waited",
            "oracle_wait_class_cluster_waited",
            "oracle_wait_class_commit_waited",
            "oracle_wait_class_concurrency_waited",
            "oracle_wait_class_configuration_waited",
            "oracle_wait_class_idle_waited",
            "oracle_wait_class_network_waited",
            "oracle_wait_class_other_waited",
            "oracle_wait_class_scheduler_waited",
            "oracle_wait_class_system_io_waited",
            "oracle_wait_class_user_io_waited",
        ],
    ),
)

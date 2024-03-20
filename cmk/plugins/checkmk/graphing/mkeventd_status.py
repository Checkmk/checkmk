#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_average_connect_rate = metrics.Metric(
    name="average_connect_rate",
    title=Title("Client connects"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)

metric_average_event_rate = metrics.Metric(
    name="average_event_rate",
    title=Title("Event creations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)

metric_average_message_rate = metrics.Metric(
    name="average_message_rate",
    title=Title("Incoming messages"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

metric_average_drop_rate = metrics.Metric(
    name="average_drop_rate",
    title=Title("Dropped messages"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

metric_average_request_time = metrics.Metric(
    name="average_request_time",
    title=Title("Average request response time"),
    unit=metrics.Unit(metrics.TimeNotation()),
    color=metrics.Color.ORANGE,
)

metric_average_rule_hit_rate = metrics.Metric(
    name="average_rule_hit_rate",
    title=Title("Rule hits"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

metric_average_rule_trie_rate = metrics.Metric(
    name="average_rule_trie_rate",
    title=Title("Rule tries"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

metric_num_open_events = metrics.Metric(
    name="num_open_events",
    title=Title("Current events"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

graph_message_processing = graphs.Graph(
    name="message_processing",
    title=Title("Message processing"),
    simple_lines=[
        "average_message_rate",
        "average_drop_rate",
    ],
)

graph_rule_efficiency = graphs.Graph(
    name="rule_efficiency",
    title=Title("Rule efficiency"),
    simple_lines=[
        "average_rule_trie_rate",
        "average_rule_hit_rate",
    ],
)

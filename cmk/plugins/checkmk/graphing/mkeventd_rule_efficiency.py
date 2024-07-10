#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

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

graph_rule_efficiency = graphs.Graph(
    name="rule_efficiency",
    title=Title("Rule efficiency"),
    simple_lines=[
        "average_rule_trie_rate",
        "average_rule_hit_rate",
    ],
)

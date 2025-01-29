#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_oracle_db_block_gets = metrics.Metric(
    name="oracle_db_block_gets",
    title=Title("Oracle block gets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_oracle_db_block_change = metrics.Metric(
    name="oracle_db_block_change",
    title=Title("Oracle block change"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_oracle_consistent_gets = metrics.Metric(
    name="oracle_consistent_gets",
    title=Title("Oracle consistent gets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_free_buffer_wait = metrics.Metric(
    name="oracle_free_buffer_wait",
    title=Title("Oracle free buffer wait"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BROWN,
)
metric_oracle_buffer_busy_wait = metrics.Metric(
    name="oracle_buffer_busy_wait",
    title=Title("Oracle buffer busy wait"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

graph_oracle_buffer_pool_statistics = graphs.Graph(
    name="oracle_buffer_pool_statistics",
    title=Title("Oracle buffer pool statistics"),
    simple_lines=[
        "oracle_db_block_gets",
        "oracle_db_block_change",
        "oracle_consistent_gets",
        "oracle_free_buffer_wait",
        "oracle_buffer_busy_wait",
    ],
)

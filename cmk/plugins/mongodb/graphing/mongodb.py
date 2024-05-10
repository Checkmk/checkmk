#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_assert_msg = metrics.Metric(
    name="assert_msg",
    title=Title("Msg Asserts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
metric_assert_rollovers = metrics.Metric(
    name="assert_rollovers",
    title=Title("Rollovers Asserts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
metric_assert_regular = metrics.Metric(
    name="assert_regular",
    title=Title("Regular Asserts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_assert_warning = metrics.Metric(
    name="assert_warning",
    title=Title("Warning Asserts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_assert_user = metrics.Metric(
    name="assert_user",
    title=Title("User Asserts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_mongodb_chunk_count = metrics.Metric(
    name="mongodb_chunk_count",
    title=Title("Number of Chunks"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_GRAY,
)
metric_mongodb_jumbo_chunk_count = metrics.Metric(
    name="mongodb_jumbo_chunk_count",
    title=Title("Jumbo Chunks"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_GRAY,
)
metric_mongodb_collection_size = metrics.Metric(
    name="mongodb_collection_size",
    title=Title("Collection Size"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_PURPLE,
)
metric_mongodb_collection_storage_size = metrics.Metric(
    name="mongodb_collection_storage_size",
    title=Title("Storage Size"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_GRAY,
)
metric_mongodb_collection_total_index_size = metrics.Metric(
    name="mongodb_collection_total_index_size",
    title=Title("Total Index Size"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_GRAY,
)
metric_mongodb_replication_info_log_size = metrics.Metric(
    name="mongodb_replication_info_log_size",
    title=Title("Total size of the oplog"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_PURPLE,
)
metric_mongodb_replication_info_used = metrics.Metric(
    name="mongodb_replication_info_used",
    title=Title("Total amount of space used by the oplog"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_GRAY,
)
metric_mongodb_replication_info_time_diff = metrics.Metric(
    name="mongodb_replication_info_time_diff",
    title=Title("Difference between the first and last operation in the oplog"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_GRAY,
)
metric_mongodb_document_count = metrics.Metric(
    name="mongodb_document_count",
    title=Title("Number of Documents"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_GRAY,
)

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.graphing._graph_metric_expressions import (
    GaugeLast,
    QueryDataKey,
)
from cmk.utils.metrics import MetricName


def _query_data_key(aggregator: dict[str, object] | None) -> QueryDataKey:
    return QueryDataKey(
        metric_name=MetricName("m"),
        consolidation_function=GaugeLast(lookback_seconds=60.0),
        attribute_filter={},
        aggregator=aggregator,
    )


def test_query_data_key_identity_includes_the_aggregator() -> None:
    aggregator: dict[str, object] = {
        "stages": [{"aggregate_by": [], "aggregation_fn": {"type": "scalar"}}]
    }
    grouped = _query_data_key(dict(aggregator))
    ungrouped = _query_data_key(None)
    assert grouped != ungrouped
    assert hash(grouped) != hash(ungrouped)
    assert grouped == _query_data_key(dict(aggregator))
    assert hash(grouped) == hash(_query_data_key(dict(aggregator)))

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.gui.graphing import (
    consolidation_function_from_wire,
    ConsolidationFunction,
    GaugeLast,
    GaugeMax,
    GraphLineGroupByKey,
    HistogramCountRate,
    HistogramFractionBetween,
    HistogramPreserveQuantile,
    QueryDataKey,
    SumRate,
)
from cmk.shared_typing import consolidation as wire


def _query_data_key(aggregator: dict[str, object] | None) -> QueryDataKey:
    return QueryDataKey(
        metric_name="m",
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


@pytest.mark.parametrize(
    "stored, expected",
    [
        pytest.param(
            wire.ConsolidationGauge(type="gauge", function="gauge_max", lookback_seconds=120.0),
            GaugeMax(lookback_seconds=120.0),
            id="gauge",
        ),
        pytest.param(
            wire.ConsolidationSum(type="sum", function="sum_rate", lookback_seconds=60.0),
            SumRate(lookback_seconds=60.0),
            id="sum",
        ),
        pytest.param(
            wire.ConsolidationHistogramScalar(
                type="histogram", function="histogram_count_rate", lookback_seconds=60.0
            ),
            HistogramCountRate(lookback_seconds=60.0),
            id="histogram scalar",
        ),
        pytest.param(
            wire.ConsolidationHistogramFractionBetween(
                type="histogram",
                function="histogram_fraction_between",
                lookback_seconds=60.0,
                lower_threshold=0.1,
                upper_threshold=0.5,
            ),
            HistogramFractionBetween(
                lookback_seconds=60.0, lower_threshold=0.1, upper_threshold=0.5
            ),
            id="histogram fraction between",
        ),
        pytest.param(
            wire.ConsolidationHistogramPreserveQuantile(
                type="histogram",
                function="histogram_preserve_quantile",
                lookback_seconds=60.0,
                percentile=90.0,
                group_by=[wire.ConsolidationGroupByKey(kind="resource", key="service.name")],
            ),
            HistogramPreserveQuantile(
                lookback_seconds=60.0,
                percentile=90.0,
                group_by=(GraphLineGroupByKey(kind="resource", key="service.name"),),
            ),
            id="histogram preserve quantile",
        ),
    ],
)
def test_a_stored_consolidation_becomes_the_one_the_gui_fetches_with(
    stored: wire.ConsolidationFunction, expected: ConsolidationFunction
) -> None:
    assert consolidation_function_from_wire(stored) == expected

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.graphing._graph_metric_expressions import (
    _time_series_math,
    GaugeLast,
    Operators,
    QueryDataKey,
)
from cmk.gui.graphing._time_series import TimeSeries
from cmk.utils.metrics import MetricName


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("%", []), id="Unknown symbol"),
    ],
)
def test__time_series_math_exc_symbol(args: tuple[Literal["%"], list[TimeSeries]]) -> None:
    with pytest.raises(MKGeneralException, match="Undefined operator"):
        _time_series_math(*args)  # type: ignore[arg-type]


@pytest.mark.parametrize("operator", ["+", "*", "MAX", "MIN", "AVERAGE", "MERGE"])
def test__time_series_math_stable_singles(operator: Operators) -> None:
    test_ts = TimeSeries(
        start=0,
        end=180,
        step=60,
        values=[6, 5, 10, None, -2, -3.14],
    )
    assert _time_series_math(operator, [test_ts]) == test_ts


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

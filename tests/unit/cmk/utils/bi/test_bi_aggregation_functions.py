#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import pytest

from cmk.utils.bi.bi_aggregation_functions import (
    BIAggregationFunctionBest,
    BIAggregationFunctionCountOK,
    BIAggregationFunctionWorst,
)


@pytest.mark.parametrize(
    "states, expected_best_state, expected_worst_state",
    [
        ([0, 0], 0, 0),
        ([0, 1], 0, 1),
        ([1, 0], 0, 1),
        ([1, 1], 1, 1),
        ([1, 2], 1, 2),
        ([2, 2], 2, 2),
        ([-1, 2], -1, 2),
        ([-1, -1], -1, -1),
    ],
)
def test_aggr_default(states, expected_best_state, expected_worst_state) -> None:
    best_aggr_config = BIAggregationFunctionBest.schema()().dump({})
    best_aggr_function = BIAggregationFunctionBest(best_aggr_config)
    assert best_aggr_function.aggregate(states) == expected_best_state

    worst_aggr_config = BIAggregationFunctionWorst.schema()().dump({})
    worst_aggr_function = BIAggregationFunctionWorst(worst_aggr_config)
    assert worst_aggr_function.aggregate(states) == expected_worst_state


@pytest.mark.parametrize(
    "states, expected_best_state, expected_worst_state",
    [
        ([0, 0], 0, 0),
        ([0, 1], 1, 0),
        ([1, 0], 1, 0),
        ([1, 1], 1, 1),
        ([1, 2], 2, 1),
        ([-1, 2], 2, -1),
        ([-1, -1], -1, -1),
    ],
)
def test_aggr_exceed_count(states, expected_best_state, expected_worst_state) -> None:
    best_aggr_config = BIAggregationFunctionBest.schema()().dump({"count": 5})
    best_aggr_function = BIAggregationFunctionBest(best_aggr_config)
    assert best_aggr_function.aggregate(states) == expected_best_state

    worst_aggr_config = BIAggregationFunctionWorst.schema()().dump({"count": 5})
    worst_aggr_function = BIAggregationFunctionWorst(worst_aggr_config)
    assert worst_aggr_function.aggregate(states) == expected_worst_state


@pytest.mark.parametrize(
    "states, expected_best_state, expected_worst_state",
    [
        ([0, 0], 0, 0),
        ([1, 0], 0, 1),
        ([0, 1], 0, 1),
        ([1, 1], 1, 1),
        ([1, 2], 1, 1),
        ([2, 2], 1, 1),
        ([-1, 2], -1, 1),
        ([-1, -1], -1, -1),
    ],
)
def test_aggr_restrict_state_warn(states, expected_best_state, expected_worst_state) -> None:
    best_aggr_config = BIAggregationFunctionBest.schema()().dump({"restrict_state": 1})
    best_aggr_function = BIAggregationFunctionBest(best_aggr_config)
    assert best_aggr_function.aggregate(states) == expected_best_state

    worst_aggr_config = BIAggregationFunctionWorst.schema()().dump({"restrict_state": 1})
    worst_aggr_function = BIAggregationFunctionWorst(worst_aggr_config)
    assert worst_aggr_function.aggregate(states) == expected_worst_state


@pytest.mark.parametrize(
    "states, ok_type, ok_value, warn_type, warn_value, expected_state",
    [
        ([0, 0, 0, 0], "count", 1, "count", 1, 0),
        ([0, 0, 0, 0], "count", 5, "count", 1, 1),
        ([0, 0, 1, 1], "count", 3, "count", 1, 1),
        ([0, 0, 1, 1], "count", 3, "count", 3, 2),
        ([0, 0, 0, 0], "percentage", 50, "count", 1, 0),
        ([0, 1, 1, 1], "percentage", 50, "count", 1, 1),
        ([0, 1, 1, 1], "percentage", 25, "count", 1, 0),
        ([0, 1, 1, 1], "percentage", 26, "count", 1, 1),
        ([0, 1, 1, 1], "percentage", 50, "percentage", 25, 1),
        ([1, 1, 1, 1], "percentage", 50, "percentage", 0, 1),
        ([1, 1, 1, 1], "percentage", 50, "percentage", 1, 2),
    ],
)
def test_aggr_count_ok(states, ok_type, ok_value, warn_type, warn_value, expected_state) -> None:
    schema_config = {
        "levels_ok": {"type": ok_type, "value": ok_value},
        "levels_warn": {"type": warn_type, "value": warn_value},
    }
    aggr_config = BIAggregationFunctionCountOK.schema()().dump(schema_config)
    aggr_function = BIAggregationFunctionCountOK(aggr_config)
    assert aggr_function.aggregate(states) == expected_state

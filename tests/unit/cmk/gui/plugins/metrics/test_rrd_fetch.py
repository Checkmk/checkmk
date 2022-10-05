#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from livestatus import LivestatusRow

import cmk.gui.plugins.metrics.rrd_fetch as rf
from cmk.gui.plugins.metrics.utils import GraphRecipe

QUERY_RESULT = LivestatusRow(
    [
        [1663730700, 1663745160, 60, None, 52.05, 52.05, 51.05, 50, None],
        [1663730700, 1663745160, 60, None, None, 54.05, 55.05, 56.05, 51, None],
    ]
)
QUERY_RESULT_CONVERTED = LivestatusRow(
    [
        [1663730700, 1663745160, 60, None, 125.69, 125.69, 123.89, 122.0, None],
        [1663730700, 1663745160, 60, None, None, 129.29, 131.09, 132.89, 123.8, None],
    ]
)


def test_needed_elements_of_expression() -> None:
    assert set(
        rf.needed_elements_of_expression(
            (
                "transformation",
                ("q90percentile", 95.0),
                [("rrd", "heute", "CPU utilization", "util", "max")],
            ),
            lambda *args: (),
        )
    ) == {("heute", "CPU utilization", "util", "max")}


@pytest.mark.parametrize(
    "query_results, graph_recipe, expected_results",
    [
        (QUERY_RESULT, {"unit": "f", "source_unit": "c"}, QUERY_RESULT_CONVERTED),
        (QUERY_RESULT, {"unit": "f"}, QUERY_RESULT),
        (QUERY_RESULT, {"source_unit": "c"}, QUERY_RESULT),
        (QUERY_RESULT, {}, QUERY_RESULT),
        (QUERY_RESULT, {"unit": "c", "source_unit": "c"}, QUERY_RESULT),
        (QUERY_RESULT, {"unit": "not_existing_unit", "source_unit": "c"}, QUERY_RESULT),
    ],
)
def test_convert_query_results(
    query_results: LivestatusRow, graph_recipe: GraphRecipe, expected_results: LivestatusRow
) -> None:
    assert rf._convert_query_results(query_results, graph_recipe) == expected_results

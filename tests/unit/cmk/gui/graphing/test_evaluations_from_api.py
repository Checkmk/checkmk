#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing import v1 as graphing_api
from cmk.graphing.v1 import graphs as graphs_api
from cmk.gui.graphing._evaluations_from_api import evaluate_graph_plugin_range
from cmk.gui.graphing._graph_specification import MinimalVerticalRange
from cmk.gui.graphing._translated_metrics import (
    Original,
    ScalarBounds,
    TranslatedMetric,
)
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation
from cmk.gui.unit_formatter import AutoPrecision


@pytest.mark.parametrize(
    "graph_plugin, expected",
    [
        pytest.param(
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                compound_lines=["metric"],
            ),
            None,
            id="graph-no-range",
        ),
        pytest.param(
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                minimal_range=graphs_api.MinimalRange(1, 200),
                compound_lines=["metric"],
            ),
            MinimalVerticalRange(min=1.0, max=200.0),
            id="graph-with-range-numbers",
        ),
        pytest.param(
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                minimal_range=graphs_api.MinimalRange(1, "metric"),
                compound_lines=["metric"],
            ),
            MinimalVerticalRange(min=1.0, max=123.456),
            id="graph-with-range-upper-known-metric",
        ),
        pytest.param(
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                minimal_range=graphs_api.MinimalRange(1, "unknown_metric"),
                compound_lines=["metric"],
            ),
            MinimalVerticalRange(min=1.0, max=None),
            id="graph-with-range-upper-metric",
        ),
        pytest.param(
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                minimal_range=graphs_api.MinimalRange("metric", 200),
                compound_lines=["metric"],
            ),
            MinimalVerticalRange(min=123.456, max=200),
            id="graph-with-range-lower-known-metric",
        ),
        pytest.param(
            graphs_api.Graph(
                name="graph",
                title=graphing_api.Title("Graph"),
                minimal_range=graphs_api.MinimalRange("unknown_metric", 200),
                compound_lines=["metric"],
            ),
            MinimalVerticalRange(min=None, max=200),
            id="graph-with-range-lower-metric",
        ),
        pytest.param(
            graphs_api.Bidirectional(
                name="graph",
                title=graphing_api.Title("Graph"),
                upper=graphs_api.Graph(
                    name="graph_upper",
                    title=graphing_api.Title("Graph upper"),
                    minimal_range=graphs_api.MinimalRange("metric", 200),
                    compound_lines=["metric"],
                ),
                lower=graphs_api.Graph(
                    name="graph_lower",
                    title=graphing_api.Title("Graph lower"),
                    minimal_range=graphs_api.MinimalRange(0, "metric"),
                    compound_lines=["metric"],
                ),
            ),
            MinimalVerticalRange(min=0, max=200),
            id="bidirectional",
        ),
        pytest.param(
            graphs_api.Bidirectional(
                name="graph",
                title=graphing_api.Title("Graph"),
                upper=graphs_api.Graph(
                    name="graph_upper",
                    title=graphing_api.Title("Graph upper"),
                    minimal_range=graphs_api.MinimalRange("metric1", 300),
                    compound_lines=["metric"],
                ),
                lower=graphs_api.Graph(
                    name="graph_lower",
                    title=graphing_api.Title("Graph lower"),
                    minimal_range=graphs_api.MinimalRange(0, 200),
                    compound_lines=["metric"],
                ),
            ),
            MinimalVerticalRange(min=0, max=300),
            id="bidirectional-no-upper-min",
        ),
        pytest.param(
            graphs_api.Bidirectional(
                name="graph",
                title=graphing_api.Title("Graph"),
                upper=graphs_api.Graph(
                    name="graph_upper",
                    title=graphing_api.Title("Graph upper"),
                    minimal_range=graphs_api.MinimalRange(0, "metric1"),
                    compound_lines=["metric"],
                ),
                lower=graphs_api.Graph(
                    name="graph_lower",
                    title=graphing_api.Title("Graph lower"),
                    minimal_range=graphs_api.MinimalRange(100, 300),
                    compound_lines=["metric"],
                ),
            ),
            MinimalVerticalRange(min=0, max=300),
            id="bidirectional-no-upper-max",
        ),
    ],
)
def test_evaluate_graph_plugin_range(
    graph_plugin: graphs_api.Graph | graphs_api.Bidirectional, expected: MinimalVerticalRange | None
) -> None:
    assert (
        evaluate_graph_plugin_range(
            graph_plugin,
            {
                "metric": TranslatedMetric(
                    originals=[Original("metric", 1.0)],
                    value=123.456,
                    scalar=ScalarBounds(),
                    auto_graph=True,
                    title="Metric",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="U"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                )
            },
        )
        == expected
    )

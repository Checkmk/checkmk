#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import graph, Localizable, metric


def test_graph_error_missing_name() -> None:
    title = Localizable("Title")
    compound_lines = [metric.MetricName("metric-name-1")]
    simple_lines = [metric.MetricName("metric-name-2")]
    with pytest.raises(AssertionError):
        graph.Graph("", title, compound_lines=compound_lines, simple_lines=simple_lines)


def test_graph_error_missing_compound_lines_and_simple_lines() -> None:
    title = Localizable("Title")
    with pytest.raises(AssertionError):
        graph.Graph("name", title)


def test_bidirectional_error_missing_name() -> None:
    upper = graph.Graph(
        "graph-upper",
        Localizable("Title"),
        compound_lines=[metric.MetricName("metric-name-1")],
        simple_lines=[metric.MetricName("metric-name-2")],
    )
    lower = graph.Graph(
        "graph-lower",
        Localizable("Title"),
        compound_lines=[metric.MetricName("metric-name-1")],
        simple_lines=[metric.MetricName("metric-name-2")],
    )
    title = Localizable("Title")
    with pytest.raises(AssertionError):
        graph.Bidirectional("", title, upper=upper, lower=lower)

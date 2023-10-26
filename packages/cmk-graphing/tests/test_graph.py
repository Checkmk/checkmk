#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import graph, Localizable, metric


def test_graph_error_missing_name() -> None:
    with pytest.raises(AssertionError):
        graph.Graph(
            name="",
            title=Localizable("Title"),
            compound_lines=[metric.MetricName("metric-name-1")],
            simple_lines=[metric.MetricName("metric-name-2")],
        )


def test_graph_error_missing_compound_lines_and_simple_lines() -> None:
    with pytest.raises(AssertionError):
        graph.Graph(
            name="name",
            title=Localizable("Title"),
        )


def test_bidirectional_error_missing_name() -> None:
    upper = graph.Graph(
        name="graph-upper",
        title=Localizable("Title"),
        compound_lines=[metric.MetricName("metric-name-1")],
        simple_lines=[metric.MetricName("metric-name-2")],
    )
    lower = graph.Graph(
        name="graph-lower",
        title=Localizable("Title"),
        compound_lines=[metric.MetricName("metric-name-1")],
        simple_lines=[metric.MetricName("metric-name-2")],
    )
    with pytest.raises(AssertionError):
        graph.Bidirectional(
            name="",
            title=Localizable("Title"),
            upper=upper,
            lower=lower,
        )

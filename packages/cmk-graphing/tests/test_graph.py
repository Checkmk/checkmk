#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import graph, Localizable, metric


def test_graph_error_empty_name() -> None:
    title = Localizable("Title")
    with pytest.raises(ValueError):
        graph.Graph("", title, compound_lines=[metric.Name("metric-name")])


def test_graph_error_missing_compound_lines_and_simple_lines() -> None:
    name = "name"
    title = Localizable("Title")
    with pytest.raises(AssertionError):
        graph.Graph(name, title)


def test_bidirectional_error_empty_name() -> None:
    title = Localizable("Title")
    lower = graph.Graph(
        "lower",
        Localizable("Title lower"),
        compound_lines=[metric.Name("metric-name-1")],
    )
    upper = graph.Graph(
        "upper",
        Localizable("Title upper"),
        compound_lines=[metric.Name("metric-name-2")],
    )
    with pytest.raises(ValueError):
        graph.Bidirectional("", title, lower=lower, upper=upper)

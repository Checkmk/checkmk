#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import graph, Localizable


def test_minimal_range_error_lower_empty_name() -> None:
    upper = "upper"
    with pytest.raises(ValueError):
        graph.MinimalRange("", upper)


def test_minimal_range_error_upper_empty_name() -> None:
    lower = "lower"
    with pytest.raises(ValueError):
        graph.MinimalRange(lower, "")


def test_graph_error_empty_name() -> None:
    title = Localizable("Title")
    with pytest.raises(ValueError):
        graph.Graph("", title, compound_lines=["metric-name"])


def test_graph_error_missing_compound_lines_and_simple_lines() -> None:
    name = "name"
    title = Localizable("Title")
    with pytest.raises(AssertionError):
        graph.Graph(name, title)


def test_graph_error_compound_lines_empty_name() -> None:
    name = "name"
    title = Localizable("Title")
    with pytest.raises(ValueError):
        graph.Graph(name, title, compound_lines=[""])


def test_graph_error_simple_lines_empty_name() -> None:
    name = "name"
    title = Localizable("Title")
    with pytest.raises(ValueError):
        graph.Graph(name, title, simple_lines=[""])


def test_graph_error_optional_empty_name() -> None:
    name = "name"
    title = Localizable("Title")
    simple_lines = ["metric-name"]
    with pytest.raises(ValueError):
        graph.Graph(name, title, simple_lines=simple_lines, optional=[""])


def test_graph_error_conflicting_empty_name() -> None:
    name = "name"
    title = Localizable("Title")
    simple_lines = ["metric-name"]
    with pytest.raises(ValueError):
        graph.Graph(name, title, simple_lines=simple_lines, conflicting=[""])


def test_bidirectional_error_empty_name() -> None:
    title = Localizable("Title")
    lower = graph.Graph(
        "lower",
        Localizable("Title lower"),
        compound_lines=["metric-name-1"],
    )
    upper = graph.Graph(
        "upper",
        Localizable("Title upper"),
        compound_lines=["metric-name-2"],
    )
    with pytest.raises(ValueError):
        graph.Bidirectional("", title, lower=lower, upper=upper)

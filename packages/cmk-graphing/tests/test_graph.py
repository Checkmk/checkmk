#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import graphs, Title


def test_minimal_range_error_lower_empty_name() -> None:
    upper = "upper"
    with pytest.raises(ValueError):
        graphs.MinimalRange("", upper)


def test_minimal_range_error_upper_empty_name() -> None:
    lower = "lower"
    with pytest.raises(ValueError):
        graphs.MinimalRange(lower, "")


def test_graph_error_empty_name() -> None:
    title = Title("Title")
    with pytest.raises(ValueError):
        graphs.Graph(name="", title=title, compound_lines=["metric-name"])


def test_graph_error_missing_compound_lines_and_simple_lines() -> None:
    name = "name"
    title = Title("Title")
    with pytest.raises(AssertionError):
        graphs.Graph(name=name, title=title)


def test_graph_error_compound_lines_empty_name() -> None:
    name = "name"
    title = Title("Title")
    with pytest.raises(ValueError):
        graphs.Graph(name=name, title=title, compound_lines=[""])


def test_graph_error_simple_lines_empty_name() -> None:
    name = "name"
    title = Title("Title")
    with pytest.raises(ValueError):
        graphs.Graph(name=name, title=title, simple_lines=[""])


def test_graph_error_optional_empty_name() -> None:
    name = "name"
    title = Title("Title")
    simple_lines = ["metric-name"]
    with pytest.raises(ValueError):
        graphs.Graph(name=name, title=title, simple_lines=simple_lines, optional=[""])


def test_graph_error_conflicting_empty_name() -> None:
    name = "name"
    title = Title("Title")
    simple_lines = ["metric-name"]
    with pytest.raises(ValueError):
        graphs.Graph(name=name, title=title, simple_lines=simple_lines, conflicting=[""])


def test_bidirectional_error_empty_name() -> None:
    title = Title("Title")
    lower = graphs.Graph(
        name="lower",
        title=Title("Title lower"),
        compound_lines=["metric-name-1"],
    )
    upper = graphs.Graph(
        name="upper",
        title=Title("Title upper"),
        compound_lines=["metric-name-2"],
    )
    with pytest.raises(ValueError):
        graphs.Bidirectional(name="", title=title, lower=lower, upper=upper)

#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import graph, Localizable


def test_name_error() -> None:
    with pytest.raises(ValueError):
        graph.Name("")


def test_graph_error_missing_compound_lines_and_simple_lines() -> None:
    name = graph.Name("name")
    title = Localizable("Title")
    with pytest.raises(AssertionError):
        graph.Graph(name, title)

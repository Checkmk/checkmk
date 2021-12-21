#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Sequence, Tuple

import pytest
from _pytest.monkeypatch import MonkeyPatch

from cmk.gui.plugins.metrics import graph_templates
from cmk.gui.plugins.metrics.utils import GraphTemplate

_GRAPH_TEMPLATES = [
    {"id": "1", "title": "Graph 1"},
    {"id": "2", "title": "Graph 2"},
]


@pytest.mark.parametrize(
    "graph_id_info, expected_result",
    [
        pytest.param(
            {},
            list(enumerate(_GRAPH_TEMPLATES)),
            id="no index and no id",
        ),
        pytest.param(
            {"graph_index": 0},
            [(0, _GRAPH_TEMPLATES[0])],
            id="matching index and no id",
        ),
        pytest.param(
            {"graph_index": 10},
            [],
            id="non-matching index and no id",
        ),
        pytest.param(
            {"graph_id": "2"},
            [(1, _GRAPH_TEMPLATES[1])],
            id="no index and matching id",
        ),
        pytest.param(
            {"graph_id": "wrong"},
            [],
            id="no index and non-matching id",
        ),
        pytest.param(
            {
                "graph_index": 0,
                "graph_id": "1",
            },
            [(0, _GRAPH_TEMPLATES[0])],
            id="matching index and matching id",
        ),
        pytest.param(
            {
                "graph_index": 0,
                "graph_id": "2",
            },
            [],
            id="inconsistent matching index and matching id",
        ),
    ],
)
def test_matching_graph_templates(
    monkeypatch: MonkeyPatch,
    graph_id_info: Mapping[str, str],
    expected_result: Sequence[Tuple[int, GraphTemplate]],
) -> None:
    monkeypatch.setattr(
        graph_templates,
        "get_graph_templates",
        lambda _metrics: _GRAPH_TEMPLATES,
    )
    assert list(graph_templates.matching_graph_templates(graph_id_info, {})) == expected_result

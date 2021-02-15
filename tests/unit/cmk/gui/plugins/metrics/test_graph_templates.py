#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Sequence, Tuple

import pytest
from _pytest.monkeypatch import MonkeyPatch

from cmk.gui.plugins.metrics import graph_templates

_GRAPH_TEMPLATES = [
    {
        "id": "1",
        "title": "Graph 1"
    },
    {
        "id": "2",
        "title": "Graph 2"
    },
]


@pytest.mark.parametrize(
    "graph_id_info, expected_result",
    [
        pytest.param(
            {},
            list(enumerate(_GRAPH_TEMPLATES)),
            id="no index",
        ),
        pytest.param(
            {"graph_index": 0},
            [(0, _GRAPH_TEMPLATES[0])],
            id="matching index",
        ),
        pytest.param(
            {"graph_index": 10},
            [],
            id="non-matching index",
        ),
    ],
)
def test_matching_graph_templates(
    monkeypatch: MonkeyPatch,
    graph_id_info: Mapping[str, str],
    expected_result: Sequence[Tuple[int, Mapping[str, str]]],
) -> None:
    monkeypatch.setattr(
        graph_templates,
        "get_graph_templates",
        lambda _metrics: _GRAPH_TEMPLATES,
    )
    assert list(graph_templates.matching_graph_templates(graph_id_info, {})) == expected_result

#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.metrics as metrics
from cmk.gui.type_defs import UnitInfo


def test_registered_renderers() -> None:
    registered_plugins = sorted(metrics.renderer_registry.keys())
    assert registered_plugins == ["dual", "linear", "logarithmic", "stacked"]


class TestMetricometerRendererLinear:
    def _renderer(
        self,
        unit_info: UnitInfo,
    ) -> metrics.MetricometerRendererLinear:
        return metrics.MetricometerRendererLinear(
            {
                "type": "linear",
                "segments": ["my_metric"],
                "total": 100.0,
            },
            {
                "my_metric": {
                    "orig_name": ["my_metric"],
                    "value": 60.0,
                    "scalar": {"warn": 80.0, "crit": 90.0},
                    "scale": [1.0],
                    "auto_graph": True,
                    "title": "My metric",
                    "unit": unit_info,
                    "color": "#ffa000",
                }
            },
        )

    @pytest.mark.parametrize(
        ["unit_info", "expected_result"],
        [
            pytest.param(
                {
                    "title": "My unit",
                    "symbol": "U",
                    "render": str,
                    "js_render": "v => cmk.number_format.drop_dotzero(v) + ' U'",
                    "id": "u",
                    "description": "My unit",
                },
                [[(60.0, "#ffa000"), (40.0, "#bdbdbd")]],
                id="no unit conversion",
            ),
            pytest.param(
                {
                    "title": "My unit",
                    "symbol": "U",
                    "render": str,
                    "js_render": "v => cmk.number_format.drop_dotzero(v) + ' U'",
                    "id": "u",
                    "description": "My unit",
                    "conversion": lambda v: 2 * v - 10,
                },
                [
                    [
                        (60.0 / (2 * 100 - 10) * 100, "#ffa000"),
                        (100 - 60.0 / (2 * 100 - 10) * 100, "#bdbdbd"),
                    ]
                ],
                id="with unit conversion",
            ),
        ],
    )
    def test_get_stack(
        self,
        unit_info: UnitInfo,
        expected_result: metrics.MetricRendererStack,
    ) -> None:
        assert self._renderer(unit_info).get_stack() == expected_result

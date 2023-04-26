#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

import numpy as np
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


class TestMetricometerRendererLogarithmic:
    @pytest.fixture(name="renderer")
    def fixture_renderer(self) -> metrics.MetricometerRendererLogarithmic:
        return metrics.MetricometerRendererLogarithmic(
            {
                "type": "logarithmic",
                "metric": "temp",
                "half_value": 40.0,
                "exponent": 1.2,
            },
            {
                "my_metric": {
                    "orig_name": ["my_metric"],
                    "value": 123.0,
                    "scalar": {"warn": 158.0, "crit": 176.0},
                    "scale": [1.0],
                    "auto_graph": True,
                    "title": "My metric",
                    "unit": {
                        "title": "My unit",
                        "symbol": "U",
                        "render": str,
                        "js_render": "v => cmk.number_format.drop_dotzero(v) + ' U'",
                        "id": "u",
                        "description": "My unit",
                    },
                    "color": "#ffa000",
                }
            },
        )

    @pytest.mark.parametrize(
        ["conversion", "expected_result"],
        [
            pytest.param(
                lambda v: v,
                (40, 1.2),
                id="no-op conversion",
            ),
            # a purely multiplicate conversion should not lead to change in the 10%-factor
            pytest.param(
                lambda v: 0.7 * v,
                (0.7 * 40, 1.2),
                id="multiplicative stretch only",
            ),
            # a huge additive offset should lead to a multiplicate 10%-factor very close to 1
            pytest.param(
                lambda v: v + 1000000,
                (40 + 1000000, 1.0),
                id="huge additive offset",
            ),
        ],
    )
    def test_estimate_parameters_for_converted_units(
        self,
        renderer: metrics.MetricometerRendererLogarithmic,
        conversion: Callable[[float], float],
        expected_result: tuple[float, float],
    ) -> None:
        assert np.allclose(
            renderer.estimate_parameters_for_converted_units(conversion),
            expected_result,
        )

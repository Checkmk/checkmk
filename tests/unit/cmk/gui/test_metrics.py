#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from typing import Optional

import pytest

import cmk.gui.metrics as metrics
from cmk.gui.type_defs import UnitInfo


def test_registered_renderers():
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
        ["perfometer_render", "expected_result"],
        [
            pytest.param(
                None,
                "60.0",
                id="no dedicated perfometer renderer",
            ),
            pytest.param(
                lambda v: f"{2*v} U",
                "120.0 U",
                id="dedicated perfometer renderer",
            ),
        ],
    )
    def test_get_label(
        self,
        perfometer_render: Optional[Callable[[float], str]],
        expected_result: str,
    ) -> None:
        unit_info: UnitInfo = {
            "title": "My unit",
            "symbol": "U",
            "render": str,
            "js_render": "v => cmk.number_format.drop_dotzero(v) + ' U'",
            "id": "u",
            "description": "My unit",
        }
        if perfometer_render:
            unit_info["perfometer_render"] = perfometer_render
        assert self._renderer(unit_info).get_label() == expected_result


class TestMetricometerRendererLogarithmic:
    def _renderer(
        self,
        unit_info: UnitInfo,
    ) -> metrics.MetricometerRendererLogarithmic:
        return metrics.MetricometerRendererLogarithmic(
            {
                "type": "logarithmic",
                "metric": "my_metric",
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
                    "unit": unit_info,
                    "color": "#ffa000",
                }
            },
        )

    @pytest.mark.parametrize(
        ["perfometer_render", "expected_result"],
        [
            pytest.param(
                None,
                "123.0",
                id="no dedicated perfometer renderer",
            ),
            pytest.param(
                lambda v: f"{2*v} U",
                "246.0 U",
                id="dedicated perfometer renderer",
            ),
        ],
    )
    def test_get_label(
        self,
        perfometer_render: Optional[Callable[[float], str]],
        expected_result: str,
    ) -> None:
        unit_info: UnitInfo = {
            "title": "My unit",
            "symbol": "U",
            "render": str,
            "js_render": "v => cmk.number_format.drop_dotzero(v) + ' U'",
            "id": "u",
            "description": "My unit",
        }
        if perfometer_render:
            unit_info["perfometer_render"] = perfometer_render
        assert self._renderer(unit_info).get_label() == expected_result

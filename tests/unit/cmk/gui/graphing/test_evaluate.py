#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.gui.graphing._evaluate import evaluate_quantity, perfometer_matches
from cmk.gui.graphing._type_defs import ScalarBounds, TranslatedMetric

from cmk.graphing.v1 import Color, Localizable
from cmk.graphing.v1 import metric as metric_api
from cmk.graphing.v1 import perfometer as perfometer_api
from cmk.graphing.v1 import Unit


def _make_perfometer(name: str, start_idx: int) -> perfometer_api.Perfometer:
    return perfometer_api.Perfometer(
        name,
        perfometer_api.FocusRange(
            perfometer_api.Closed(f"metric-name{start_idx+1}"),
            perfometer_api.Closed(f"metric-name{start_idx+2}"),
        ),
        [
            metric_api.WarningOf(f"metric-name{start_idx+3}"),
            metric_api.CriticalOf(f"metric-name{start_idx+4}"),
            metric_api.MinimumOf(f"metric-name{start_idx+5}", Color.BLUE),
            metric_api.MaximumOf(f"metric-name{start_idx+6}", Color.BLUE),
            metric_api.Sum(
                Localizable("Title"),
                Color.BLUE,
                [
                    f"metric-name{start_idx+7}",
                    f"metric-name{start_idx+8}",
                ],
            ),
            metric_api.Product(
                Localizable("Title"),
                Unit.COUNT,
                Color.BLUE,
                [
                    f"metric-name{start_idx+9}",
                    f"metric-name{start_idx+10}",
                ],
            ),
            metric_api.Difference(
                Localizable("Title"),
                Color.BLUE,
                minuend=f"metric-name{start_idx+11}",
                subtrahend=f"metric-name{start_idx+12}",
            ),
            metric_api.Fraction(
                Localizable("Title"),
                Unit.COUNT,
                Color.BLUE,
                dividend=f"metric-name{start_idx+13}",
                divisor=f"metric-name{start_idx+14}",
            ),
        ],
    )


def _make_translated_metric(name: str, scalar: ScalarBounds) -> TranslatedMetric:
    return {
        "orig_name": [name],
        "value": 10.0,
        "scalar": scalar,
        "scale": [1.0],
        "auto_graph": False,
        "title": "Title 1",
        "unit": {
            "title": "Title 2",
            "symbol": "",
            "render": lambda v: f"{v}",
            "js_render": "v => v",
        },
        "color": "#123456",
    }


@pytest.mark.parametrize(
    "perfometer, translated_metrics, result",
    [
        pytest.param(
            _make_perfometer("name", 0),
            {
                name: _make_translated_metric(name, scalar)
                for name, scalar in (
                    ("metric-name1", ScalarBounds()),
                    ("metric-name2", ScalarBounds()),
                    ("metric-name3", ScalarBounds(warn=1)),
                    ("metric-name4", ScalarBounds(crit=2)),
                    ("metric-name5", ScalarBounds(min=3)),
                    ("metric-name6", ScalarBounds(max=4)),
                    ("metric-name7", ScalarBounds()),
                    ("metric-name8", ScalarBounds()),
                    ("metric-name9", ScalarBounds()),
                    ("metric-name10", ScalarBounds()),
                    ("metric-name11", ScalarBounds()),
                    ("metric-name12", ScalarBounds()),
                    ("metric-name13", ScalarBounds()),
                    ("metric-name14", ScalarBounds()),
                )
            },
            True,
            id="perfometer-matches",
        ),
        pytest.param(
            _make_perfometer("name", 0),
            {},
            False,
            id="perfometer-does-not-matches-no-translated-metrics",
        ),
        pytest.param(
            _make_perfometer("name", 0),
            {
                name: _make_translated_metric(name, scalar)
                for name, scalar in (
                    ("metric-name1", ScalarBounds()),
                    ("metric-name2", ScalarBounds()),
                    ("metric-name3", ScalarBounds()),
                    ("metric-name4", ScalarBounds()),
                    ("metric-name5", ScalarBounds()),
                    ("metric-name6", ScalarBounds()),
                    ("metric-name7", ScalarBounds()),
                    ("metric-name8", ScalarBounds()),
                    ("metric-name9", ScalarBounds()),
                    ("metric-name10", ScalarBounds()),
                    ("metric-name11", ScalarBounds()),
                    ("metric-name12", ScalarBounds()),
                    ("metric-name13", ScalarBounds()),
                    ("metric-name14", ScalarBounds()),
                )
            },
            False,
            id="perfometer-does-not-match-no-scalars",
        ),
        pytest.param(
            _make_perfometer("name", 14),
            {
                name: _make_translated_metric(name, scalar)
                for name, scalar in (
                    ("metric-name1", ScalarBounds()),
                    ("metric-name2", ScalarBounds()),
                    ("metric-name3", ScalarBounds(warn=1)),
                    ("metric-name4", ScalarBounds(crit=2)),
                    ("metric-name5", ScalarBounds(min=3)),
                    ("metric-name6", ScalarBounds(max=4)),
                    ("metric-name7", ScalarBounds()),
                    ("metric-name8", ScalarBounds()),
                    ("metric-name9", ScalarBounds()),
                    ("metric-name10", ScalarBounds()),
                    ("metric-name11", ScalarBounds()),
                    ("metric-name12", ScalarBounds()),
                    ("metric-name13", ScalarBounds()),
                    ("metric-name14", ScalarBounds()),
                )
            },
            False,
            id="perfometer-does-not-match-shifted-metric-names",
        ),
        pytest.param(
            perfometer_api.Bidirectional(
                "bidirectional",
                left=_make_perfometer("left", 0),
                right=_make_perfometer("right", 14),
            ),
            {
                name: _make_translated_metric(name, scalar)
                for name, scalar in (
                    ("metric-name1", ScalarBounds()),
                    ("metric-name2", ScalarBounds()),
                    ("metric-name3", ScalarBounds(warn=1)),
                    ("metric-name4", ScalarBounds(crit=2)),
                    ("metric-name5", ScalarBounds(min=3)),
                    ("metric-name6", ScalarBounds(max=4)),
                    ("metric-name7", ScalarBounds()),
                    ("metric-name8", ScalarBounds()),
                    ("metric-name9", ScalarBounds()),
                    ("metric-name10", ScalarBounds()),
                    ("metric-name11", ScalarBounds()),
                    ("metric-name12", ScalarBounds()),
                    ("metric-name13", ScalarBounds()),
                    ("metric-name14", ScalarBounds()),
                    ("metric-name15", ScalarBounds()),
                    ("metric-name16", ScalarBounds()),
                    ("metric-name17", ScalarBounds(warn=1)),
                    ("metric-name18", ScalarBounds(crit=2)),
                    ("metric-name19", ScalarBounds(min=3)),
                    ("metric-name20", ScalarBounds(max=4)),
                    ("metric-name21", ScalarBounds()),
                    ("metric-name22", ScalarBounds()),
                    ("metric-name23", ScalarBounds()),
                    ("metric-name24", ScalarBounds()),
                    ("metric-name25", ScalarBounds()),
                    ("metric-name26", ScalarBounds()),
                    ("metric-name27", ScalarBounds()),
                    ("metric-name28", ScalarBounds()),
                )
            },
            True,
            id="bidirectional-matches",
        ),
        pytest.param(
            perfometer_api.Stacked(
                "stacked",
                lower=_make_perfometer("lower", 0),
                upper=_make_perfometer("upper", 14),
            ),
            {
                name: _make_translated_metric(name, scalar)
                for name, scalar in (
                    ("metric-name1", ScalarBounds()),
                    ("metric-name2", ScalarBounds()),
                    ("metric-name3", ScalarBounds(warn=1)),
                    ("metric-name4", ScalarBounds(crit=2)),
                    ("metric-name5", ScalarBounds(min=3)),
                    ("metric-name6", ScalarBounds(max=4)),
                    ("metric-name7", ScalarBounds()),
                    ("metric-name8", ScalarBounds()),
                    ("metric-name9", ScalarBounds()),
                    ("metric-name10", ScalarBounds()),
                    ("metric-name11", ScalarBounds()),
                    ("metric-name12", ScalarBounds()),
                    ("metric-name13", ScalarBounds()),
                    ("metric-name14", ScalarBounds()),
                    ("metric-name15", ScalarBounds()),
                    ("metric-name16", ScalarBounds()),
                    ("metric-name17", ScalarBounds(warn=1)),
                    ("metric-name18", ScalarBounds(crit=2)),
                    ("metric-name19", ScalarBounds(min=3)),
                    ("metric-name20", ScalarBounds(max=4)),
                    ("metric-name21", ScalarBounds()),
                    ("metric-name22", ScalarBounds()),
                    ("metric-name23", ScalarBounds()),
                    ("metric-name24", ScalarBounds()),
                    ("metric-name25", ScalarBounds()),
                    ("metric-name26", ScalarBounds()),
                    ("metric-name27", ScalarBounds()),
                    ("metric-name28", ScalarBounds()),
                )
            },
            True,
            id="stacked-matches",
        ),
    ],
)
def test_perfometer_matches(
    perfometer: perfometer_api.Perfometer | perfometer_api.Bidirectional | perfometer_api.Stacked,
    translated_metrics: Mapping[str, TranslatedMetric],
    result: bool,
) -> None:
    assert perfometer_matches(perfometer, translated_metrics) is result


@pytest.mark.parametrize(
    "quantity, translated_metrics, result",
    [
        pytest.param(
            "name",
            {
                "name": {
                    "orig_name": ["name"],
                    "value": 10.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": {
                        "title": "Title 2",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#123456",
                }
            },
            10.0,
            id="metric-name",
        ),
        pytest.param(
            metric_api.Constant(
                Localizable("Title"),
                Unit.COUNT,
                Color.BLUE,
                5.0,
            ),
            {
                "name": {
                    "orig_name": ["name"],
                    "value": 10.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": {
                        "title": "Title 2",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#123456",
                }
            },
            5.0,
            id="metric.Constant",
        ),
        pytest.param(
            metric_api.WarningOf("name"),
            {
                "name": {
                    "orig_name": ["name"],
                    "value": 10.0,
                    "scalar": {"warn": 5.0},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": {
                        "title": "Title 2",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#123456",
                }
            },
            5.0,
            id="metric.WarningOf",
        ),
        pytest.param(
            metric_api.CriticalOf("name"),
            {
                "name": {
                    "orig_name": ["name"],
                    "value": 10.0,
                    "scalar": {"crit": 5.0},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": {
                        "title": "Title 2",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#123456",
                }
            },
            5.0,
            id="metric.CriticalOf",
        ),
        pytest.param(
            metric_api.MinimumOf("name", Color.BLUE),
            {
                "name": {
                    "orig_name": ["name"],
                    "value": 10.0,
                    "scalar": {"min": 5.0},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": {
                        "title": "Title 2",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#123456",
                }
            },
            5.0,
            id="metric.MinimumOf",
        ),
        pytest.param(
            metric_api.MaximumOf("name", Color.BLUE),
            {
                "name": {
                    "orig_name": ["name"],
                    "value": 10.0,
                    "scalar": {"max": 5.0},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": {
                        "title": "Title 2",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#123456",
                }
            },
            5.0,
            id="metric.MaximumOf",
        ),
        pytest.param(
            metric_api.Sum(
                Localizable("Title"),
                Color.BLUE,
                ["name1", "name2"],
            ),
            {
                "name1": {
                    "orig_name": ["name1"],
                    "value": 10.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": {
                        "title": "Title 2",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#123456",
                },
                "name2": {
                    "orig_name": ["name2"],
                    "value": 5.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": {
                        "title": "Title 2",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#123456",
                },
            },
            15.0,
            id="metric.Sum",
        ),
        pytest.param(
            metric_api.Product(
                Localizable("Title"),
                Unit.COUNT,
                Color.BLUE,
                ["name1", "name2"],
            ),
            {
                "name1": {
                    "orig_name": ["name1"],
                    "value": 10.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": {
                        "title": "Title 2",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#123456",
                },
                "name2": {
                    "orig_name": ["name2"],
                    "value": 5.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": {
                        "title": "Title 2",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#123456",
                },
            },
            50.0,
            id="metric.Product",
        ),
        pytest.param(
            metric_api.Difference(
                Localizable("Title"),
                Color.BLUE,
                minuend="name1",
                subtrahend="name2",
            ),
            {
                "name1": {
                    "orig_name": ["name1"],
                    "value": 10.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": {
                        "title": "Title 2",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#123456",
                },
                "name2": {
                    "orig_name": ["name2"],
                    "value": 3.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": {
                        "title": "Title 2",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#123456",
                },
            },
            7.0,
            id="metric.Fraction",
        ),
        pytest.param(
            metric_api.Fraction(
                Localizable("Title"),
                Unit.COUNT,
                Color.BLUE,
                dividend="name1",
                divisor="name2",
            ),
            {
                "name1": {
                    "orig_name": ["name1"],
                    "value": 10.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": {
                        "title": "Title 2",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#123456",
                },
                "name2": {
                    "orig_name": ["name2"],
                    "value": 5.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": {
                        "title": "Title 2",
                        "symbol": "",
                        "render": lambda v: f"{v}",
                        "js_render": "v => v",
                    },
                    "color": "#123456",
                },
            },
            2.0,
            id="metric.Fraction",
        ),
    ],
)
def test_evaluate_quantity(
    quantity: (
        str
        | metric_api.Constant
        | metric_api.WarningOf
        | metric_api.CriticalOf
        | metric_api.MinimumOf
        | metric_api.MaximumOf
        | metric_api.Sum
        | metric_api.Product
        | metric_api.Difference
        | metric_api.Fraction
    ),
    translated_metrics: Mapping[str, TranslatedMetric],
    result: float,
) -> None:
    assert evaluate_quantity(quantity, translated_metrics).value == result

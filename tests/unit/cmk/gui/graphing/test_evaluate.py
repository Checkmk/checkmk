#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.gui.graphing._evaluate import evaluate_quantity, perfometer_matches
from cmk.gui.graphing._type_defs import ScalarBounds, TranslatedMetric
from cmk.gui.graphing._unit_info import UnitInfo

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT = metrics.Unit(metrics.DecimalNotation(""))


def _make_perfometer(name: str, start_idx: int) -> perfometers.Perfometer:
    return perfometers.Perfometer(
        name=name,
        focus_range=perfometers.FocusRange(
            perfometers.Closed(f"metric-name{start_idx + 1}"),
            perfometers.Closed(f"metric-name{start_idx + 2}"),
        ),
        segments=[
            metrics.WarningOf(f"metric-name{start_idx + 3}"),
            metrics.CriticalOf(f"metric-name{start_idx + 4}"),
            metrics.MinimumOf(f"metric-name{start_idx + 5}", metrics.Color.BLUE),
            metrics.MaximumOf(f"metric-name{start_idx + 6}", metrics.Color.BLUE),
            metrics.Sum(
                Title("Title"),
                metrics.Color.BLUE,
                [
                    f"metric-name{start_idx + 7}",
                    f"metric-name{start_idx + 8}",
                ],
            ),
            metrics.Product(
                Title("Title"),
                UNIT,
                metrics.Color.BLUE,
                [
                    f"metric-name{start_idx + 9}",
                    f"metric-name{start_idx + 10}",
                ],
            ),
            metrics.Difference(
                Title("Title"),
                metrics.Color.BLUE,
                minuend=f"metric-name{start_idx + 11}",
                subtrahend=f"metric-name{start_idx + 12}",
            ),
            metrics.Fraction(
                Title("Title"),
                UNIT,
                metrics.Color.BLUE,
                dividend=f"metric-name{start_idx + 13}",
                divisor=f"metric-name{start_idx + 14}",
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
        "unit": UnitInfo(
            id="id",
            title="Title",
            symbol="",
            render=lambda v: f"{v}",
            js_render="v => v",
        ),
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
            perfometers.Bidirectional(
                name="bidirectional",
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
            perfometers.Stacked(
                name="stacked",
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
    perfometer: perfometers.Perfometer | perfometers.Bidirectional | perfometers.Stacked,
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
                    "unit": UnitInfo(
                        id="id",
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                    ),
                    "color": "#123456",
                }
            },
            10.0,
            id="metric-name",
        ),
        pytest.param(
            metrics.Constant(
                Title("Title"),
                UNIT,
                metrics.Color.BLUE,
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
                    "unit": UnitInfo(
                        id="id",
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                    ),
                    "color": "#123456",
                }
            },
            5.0,
            id="metrics.Constant",
        ),
        pytest.param(
            metrics.WarningOf("name"),
            {
                "name": {
                    "orig_name": ["name"],
                    "value": 10.0,
                    "scalar": {"warn": 5.0},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": UnitInfo(
                        id="id",
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                    ),
                    "color": "#123456",
                }
            },
            5.0,
            id="metrics.WarningOf",
        ),
        pytest.param(
            metrics.CriticalOf("name"),
            {
                "name": {
                    "orig_name": ["name"],
                    "value": 10.0,
                    "scalar": {"crit": 5.0},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": UnitInfo(
                        id="id",
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                    ),
                    "color": "#123456",
                }
            },
            5.0,
            id="metrics.CriticalOf",
        ),
        pytest.param(
            metrics.MinimumOf("name", metrics.Color.BLUE),
            {
                "name": {
                    "orig_name": ["name"],
                    "value": 10.0,
                    "scalar": {"min": 5.0},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": UnitInfo(
                        id="id",
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                    ),
                    "color": "#123456",
                }
            },
            5.0,
            id="metrics.MinimumOf",
        ),
        pytest.param(
            metrics.MaximumOf("name", metrics.Color.BLUE),
            {
                "name": {
                    "orig_name": ["name"],
                    "value": 10.0,
                    "scalar": {"max": 5.0},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": UnitInfo(
                        id="id",
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                    ),
                    "color": "#123456",
                }
            },
            5.0,
            id="metrics.MaximumOf",
        ),
        pytest.param(
            metrics.Sum(
                Title("Title"),
                metrics.Color.BLUE,
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
                    "unit": UnitInfo(
                        id="id",
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                    ),
                    "color": "#123456",
                },
                "name2": {
                    "orig_name": ["name2"],
                    "value": 5.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": UnitInfo(
                        id="id",
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                    ),
                    "color": "#123456",
                },
            },
            15.0,
            id="metrics.Sum",
        ),
        pytest.param(
            metrics.Product(
                Title("Title"),
                UNIT,
                metrics.Color.BLUE,
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
                    "unit": UnitInfo(
                        id="id",
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                    ),
                    "color": "#123456",
                },
                "name2": {
                    "orig_name": ["name2"],
                    "value": 5.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": UnitInfo(
                        id="id",
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                    ),
                    "color": "#123456",
                },
            },
            50.0,
            id="metrics.Product",
        ),
        pytest.param(
            metrics.Difference(
                Title("Title"),
                metrics.Color.BLUE,
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
                    "unit": UnitInfo(
                        id="id",
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                    ),
                    "color": "#123456",
                },
                "name2": {
                    "orig_name": ["name2"],
                    "value": 3.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": UnitInfo(
                        id="id",
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                    ),
                    "color": "#123456",
                },
            },
            7.0,
            id="metrics.Fraction",
        ),
        pytest.param(
            metrics.Fraction(
                Title("Title"),
                UNIT,
                metrics.Color.BLUE,
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
                    "unit": UnitInfo(
                        id="id",
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                    ),
                    "color": "#123456",
                },
                "name2": {
                    "orig_name": ["name2"],
                    "value": 5.0,
                    "scalar": {},
                    "scale": [1.0],
                    "auto_graph": False,
                    "title": "Title 1",
                    "unit": UnitInfo(
                        id="id",
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                    ),
                    "color": "#123456",
                },
            },
            2.0,
            id="metrics.Fraction",
        ),
    ],
)
def test_evaluate_quantity(
    quantity: (
        str
        | metrics.Constant
        | metrics.WarningOf
        | metrics.CriticalOf
        | metrics.MinimumOf
        | metrics.MaximumOf
        | metrics.Sum
        | metrics.Product
        | metrics.Difference
        | metrics.Fraction
    ),
    translated_metrics: Mapping[str, TranslatedMetric],
    result: float,
) -> None:
    assert evaluate_quantity(quantity, translated_metrics).value == result

#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.graphing.v1 import metrics as metrics_api
from cmk.graphing.v1 import perfometers as perfometers_api
from cmk.graphing.v1 import Title
from cmk.gui.graphing._formatter import AutoPrecision
from cmk.gui.graphing._perfometer import _evaluate_quantity, _perfometer_matches
from cmk.gui.graphing._translated_metrics import Original, ScalarBounds, TranslatedMetric
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation

UNIT = metrics_api.Unit(metrics_api.DecimalNotation(""))


def _make_perfometer(name: str, start_idx: int) -> perfometers_api.Perfometer:
    return perfometers_api.Perfometer(
        name=name,
        focus_range=perfometers_api.FocusRange(
            perfometers_api.Closed(f"metric-name{start_idx + 1}"),
            perfometers_api.Closed(f"metric-name{start_idx + 2}"),
        ),
        segments=[
            metrics_api.WarningOf(f"metric-name{start_idx + 3}"),
            metrics_api.CriticalOf(f"metric-name{start_idx + 4}"),
            metrics_api.MinimumOf(f"metric-name{start_idx + 5}", metrics_api.Color.BLUE),
            metrics_api.MaximumOf(f"metric-name{start_idx + 6}", metrics_api.Color.BLUE),
            metrics_api.Sum(
                Title("Title"),
                metrics_api.Color.BLUE,
                [
                    f"metric-name{start_idx + 7}",
                    f"metric-name{start_idx + 8}",
                ],
            ),
            metrics_api.Product(
                Title("Title"),
                UNIT,
                metrics_api.Color.BLUE,
                [
                    f"metric-name{start_idx + 9}",
                    f"metric-name{start_idx + 10}",
                ],
            ),
            metrics_api.Difference(
                Title("Title"),
                metrics_api.Color.BLUE,
                minuend=f"metric-name{start_idx + 11}",
                subtrahend=f"metric-name{start_idx + 12}",
            ),
            metrics_api.Fraction(
                Title("Title"),
                UNIT,
                metrics_api.Color.BLUE,
                dividend=f"metric-name{start_idx + 13}",
                divisor=f"metric-name{start_idx + 14}",
            ),
        ],
    )


def _make_translated_metric(name: str, scalar: ScalarBounds) -> TranslatedMetric:
    return TranslatedMetric(
        originals=[Original(name, 1.0)],
        value=10.0,
        scalar=scalar,
        auto_graph=False,
        title="Title 1",
        unit_spec=ConvertibleUnitSpecification(
            notation=DecimalNotation(symbol=""),
            precision=AutoPrecision(digits=2),
        ),
        color="#123456",
    )


def test__perfometer_matches_no_translated_metrics() -> None:
    with pytest.raises(AssertionError):
        assert _perfometer_matches(_make_perfometer("name", 0), {})


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
            perfometers_api.Bidirectional(
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
            perfometers_api.Stacked(
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
def test__perfometer_matches(
    perfometer: (
        perfometers_api.Perfometer | perfometers_api.Bidirectional | perfometers_api.Stacked
    ),
    translated_metrics: Mapping[str, TranslatedMetric],
    result: bool,
) -> None:
    assert _perfometer_matches(perfometer, translated_metrics) is result


@pytest.mark.parametrize(
    "quantity, translated_metrics, result",
    [
        pytest.param(
            "name",
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar={},
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            10.0,
            id="metric-name",
        ),
        pytest.param(
            metrics_api.Constant(
                Title("Title"),
                UNIT,
                metrics_api.Color.BLUE,
                5.0,
            ),
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar={},
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            5.0,
            id="metrics_api.Constant",
        ),
        pytest.param(
            metrics_api.WarningOf("name"),
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar={"warn": 5.0},
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            5.0,
            id="metrics_api.WarningOf",
        ),
        pytest.param(
            metrics_api.CriticalOf("name"),
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar={"crit": 5.0},
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            5.0,
            id="metrics_api.CriticalOf",
        ),
        pytest.param(
            metrics_api.MinimumOf("name", metrics_api.Color.BLUE),
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar={"min": 5.0},
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            5.0,
            id="metrics_api.MinimumOf",
        ),
        pytest.param(
            metrics_api.MaximumOf("name", metrics_api.Color.BLUE),
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar={"max": 5.0},
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            5.0,
            id="metrics_api.MaximumOf",
        ),
        pytest.param(
            metrics_api.Sum(
                Title("Title"),
                metrics_api.Color.BLUE,
                ["name1", "name2"],
            ),
            {
                "name1": TranslatedMetric(
                    originals=[Original("name1", 1.0)],
                    value=10.0,
                    scalar={},
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
                "name2": TranslatedMetric(
                    originals=[Original("name2", 1.0)],
                    value=5.0,
                    scalar={},
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            15.0,
            id="metrics_api.Sum",
        ),
        pytest.param(
            metrics_api.Product(
                Title("Title"),
                UNIT,
                metrics_api.Color.BLUE,
                ["name1", "name2"],
            ),
            {
                "name1": TranslatedMetric(
                    originals=[Original("name1", 1.0)],
                    value=10.0,
                    scalar={},
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
                "name2": TranslatedMetric(
                    originals=[Original("name2", 1.0)],
                    value=5.0,
                    scalar={},
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            50.0,
            id="metrics_api.Product",
        ),
        pytest.param(
            metrics_api.Difference(
                Title("Title"),
                metrics_api.Color.BLUE,
                minuend="name1",
                subtrahend="name2",
            ),
            {
                "name1": TranslatedMetric(
                    originals=[Original("name1", 1.0)],
                    value=10.0,
                    scalar={},
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
                "name2": TranslatedMetric(
                    originals=[Original("name2", 1.0)],
                    value=3.0,
                    scalar={},
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            7.0,
            id="metrics_api.Fraction",
        ),
        pytest.param(
            metrics_api.Fraction(
                Title("Title"),
                UNIT,
                metrics_api.Color.BLUE,
                dividend="name1",
                divisor="name2",
            ),
            {
                "name1": TranslatedMetric(
                    originals=[Original("name1", 1.0)],
                    value=10.0,
                    scalar={},
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
                "name2": TranslatedMetric(
                    originals=[Original("name2", 1.0)],
                    value=5.0,
                    scalar={},
                    auto_graph=False,
                    title="Title 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#123456",
                ),
            },
            2.0,
            id="metrics_api.Fraction",
        ),
    ],
)
def test__evaluate_quantity(
    quantity: (
        str
        | metrics_api.Constant
        | metrics_api.WarningOf
        | metrics_api.CriticalOf
        | metrics_api.MinimumOf
        | metrics_api.MaximumOf
        | metrics_api.Sum
        | metrics_api.Product
        | metrics_api.Difference
        | metrics_api.Fraction
    ),
    translated_metrics: Mapping[str, TranslatedMetric],
    result: float,
) -> None:
    assert _evaluate_quantity(quantity, translated_metrics).value == result

#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import perfometers as perfometers_v1
from cmk.graphing.v1 import Title
from cmk.graphing.v2_unstable import metrics as metrics_v2_unstable
from cmk.gui.graphing._evaluations_from_api import evaluate_quantity
from cmk.gui.graphing._perfometer import _perfometer_plugin_matches
from cmk.gui.graphing._translated_metrics import (
    Original,
    ScalarBounds,
    TranslatedMetric,
)
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation
from cmk.gui.unit_formatter import AutoPrecision

UNIT = metrics_v1.Unit(metrics_v1.DecimalNotation(""))


def _make_perfometer(name: str, start_idx: int) -> perfometers_v1.Perfometer:
    return perfometers_v1.Perfometer(
        name=name,
        focus_range=perfometers_v1.FocusRange(
            perfometers_v1.Closed(f"metric-name{start_idx + 1}"),
            perfometers_v1.Closed(f"metric-name{start_idx + 2}"),
        ),
        segments=[
            metrics_v1.WarningOf(f"metric-name{start_idx + 3}"),
            metrics_v1.CriticalOf(f"metric-name{start_idx + 4}"),
            metrics_v1.MinimumOf(f"metric-name{start_idx + 5}", metrics_v1.Color.BLUE),
            metrics_v1.MaximumOf(f"metric-name{start_idx + 6}", metrics_v1.Color.BLUE),
            metrics_v1.Sum(
                Title("Title"),
                metrics_v1.Color.BLUE,
                [
                    f"metric-name{start_idx + 7}",
                    f"metric-name{start_idx + 8}",
                ],
            ),
            metrics_v1.Product(
                Title("Title"),
                UNIT,
                metrics_v1.Color.BLUE,
                [
                    f"metric-name{start_idx + 9}",
                    f"metric-name{start_idx + 10}",
                ],
            ),
            metrics_v1.Difference(
                Title("Title"),
                metrics_v1.Color.BLUE,
                minuend=f"metric-name{start_idx + 11}",
                subtrahend=f"metric-name{start_idx + 12}",
            ),
            metrics_v1.Fraction(
                Title("Title"),
                UNIT,
                metrics_v1.Color.BLUE,
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


def test__perfometer_plugin_matches_no_translated_metrics() -> None:
    with pytest.raises(AssertionError):
        assert _perfometer_plugin_matches(_make_perfometer("name", 0), {})


@pytest.mark.parametrize(
    "perfometer_plugin, translated_metrics, result",
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
                    ("metric-name5", ScalarBounds(min_=3)),
                    ("metric-name6", ScalarBounds(max_=4)),
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
                    ("metric-name5", ScalarBounds(min_=3)),
                    ("metric-name6", ScalarBounds(max_=4)),
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
            perfometers_v1.Bidirectional(
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
                    ("metric-name5", ScalarBounds(min_=3)),
                    ("metric-name6", ScalarBounds(max_=4)),
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
                    ("metric-name19", ScalarBounds(min_=3)),
                    ("metric-name20", ScalarBounds(max_=4)),
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
            perfometers_v1.Stacked(
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
                    ("metric-name5", ScalarBounds(min_=3)),
                    ("metric-name6", ScalarBounds(max_=4)),
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
                    ("metric-name19", ScalarBounds(min_=3)),
                    ("metric-name20", ScalarBounds(max_=4)),
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
def test__perfometer_plugin_matches(
    perfometer_plugin: (
        perfometers_v1.Perfometer | perfometers_v1.Bidirectional | perfometers_v1.Stacked
    ),
    translated_metrics: Mapping[str, TranslatedMetric],
    result: bool,
) -> None:
    assert _perfometer_plugin_matches(perfometer_plugin, translated_metrics) is result


@pytest.mark.parametrize(
    "quantity, translated_metrics, expected_value",
    [
        pytest.param(
            "name",
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(),
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
            metrics_v1.Constant(
                Title("Title"),
                UNIT,
                metrics_v1.Color.BLUE,
                5.0,
            ),
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(),
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
            id="metrics_v1.Constant",
        ),
        pytest.param(
            metrics_v1.WarningOf("name"),
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(warn=5.0),
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
            id="metrics_v1.WarningOf",
        ),
        pytest.param(
            metrics_v1.CriticalOf("name"),
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(crit=5.0),
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
            id="metrics_v1.CriticalOf",
        ),
        pytest.param(
            metrics_v1.MinimumOf("name", metrics_v1.Color.BLUE),
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(min_=5.0),
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
            id="metrics_v1.MinimumOf",
        ),
        pytest.param(
            metrics_v1.MaximumOf("name", metrics_v1.Color.BLUE),
            {
                "name": TranslatedMetric(
                    originals=[Original("name", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(max_=5.0),
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
            id="metrics_v1.MaximumOf",
        ),
        pytest.param(
            metrics_v1.Sum(
                Title("Title"),
                metrics_v1.Color.BLUE,
                ["name1", "name2"],
            ),
            {
                "name1": TranslatedMetric(
                    originals=[Original("name1", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(),
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
                    scalar=ScalarBounds(),
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
            id="metrics_v1.Sum",
        ),
        pytest.param(
            metrics_v1.Product(
                Title("Title"),
                UNIT,
                metrics_v1.Color.BLUE,
                ["name1", "name2"],
            ),
            {
                "name1": TranslatedMetric(
                    originals=[Original("name1", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(),
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
                    scalar=ScalarBounds(),
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
            id="metrics_v1.Product",
        ),
        pytest.param(
            metrics_v1.Difference(
                Title("Title"),
                metrics_v1.Color.BLUE,
                minuend="name1",
                subtrahend="name2",
            ),
            {
                "name1": TranslatedMetric(
                    originals=[Original("name1", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(),
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
                    scalar=ScalarBounds(),
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
            id="metrics_v1.Fraction",
        ),
        pytest.param(
            metrics_v1.Fraction(
                Title("Title"),
                UNIT,
                metrics_v1.Color.BLUE,
                dividend="name1",
                divisor="name2",
            ),
            {
                "name1": TranslatedMetric(
                    originals=[Original("name1", 1.0)],
                    value=10.0,
                    scalar=ScalarBounds(),
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
                    scalar=ScalarBounds(),
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
            id="metrics_v1.Fraction",
        ),
        pytest.param(
            metrics_v2_unstable.LowerWarningOf("name"),
            {
                "name": _make_translated_metric("name", ScalarBounds(warn=99.0, warn_lower=3.0)),
            },
            3.0,
            id="metrics_v2_unstable.LowerWarningOf",
        ),
        pytest.param(
            metrics_v2_unstable.LowerCriticalOf("name"),
            {
                "name": _make_translated_metric("name", ScalarBounds(crit=99.0, crit_lower=2.0)),
            },
            2.0,
            id="metrics_v2_unstable.LowerCriticalOf",
        ),
    ],
)
def test_evaluate_quantity(
    quantity: (
        str
        | metrics_v1.Constant
        | metrics_v1.WarningOf
        | metrics_v1.CriticalOf
        | metrics_v1.MinimumOf
        | metrics_v1.MaximumOf
        | metrics_v1.Sum
        | metrics_v1.Product
        | metrics_v1.Difference
        | metrics_v1.Fraction
        | metrics_v2_unstable.LowerWarningOf
        | metrics_v2_unstable.LowerCriticalOf
    ),
    translated_metrics: Mapping[str, TranslatedMetric],
    expected_value: float,
) -> None:
    result = evaluate_quantity({}, quantity, translated_metrics)
    assert result.is_ok()
    assert result.ok.value == expected_value

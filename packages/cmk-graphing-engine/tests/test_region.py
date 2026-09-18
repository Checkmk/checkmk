#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import (
    AutoPrecision,
    ConsolidationFunction,
    Constant,
    Curve,
    CurveAttributes,
    DecimalNotation,
    evaluate_graphs,
    EvaluatedGraph,
    FetchedData,
    Graph,
    Region,
    RRDMetric,
    Unit,
)

from ._fixtures import _FakeRRDFetchData, _metric, _time_series, _TR

_UNIT = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))
_ATTRIBUTES = CurveAttributes(title="confidence interval", unit=_UNIT, color="#F4E750")


def _curve(quantity: Constant | RRDMetric) -> Curve:
    return Curve(quantity=quantity, attributes=_ATTRIBUTES)


def _graph_of(region: Region) -> Graph:
    return Graph(name="n", title="t", kind="template", regions=[region])


def _evaluate(region: Region, fetch_data: _FakeRRDFetchData) -> EvaluatedGraph:
    return evaluate_graphs(
        consolidation_function=ConsolidationFunction.MAX,
        time_range=_TR,
        graphs=[_graph_of(region)],
        fetch_data=fetch_data,
    )[0]


def _fetched(metric: RRDMetric, *values: float | None) -> _FakeRRDFetchData:
    return _FakeRRDFetchData(
        {metric: [FetchedData(performance_data=None, time_series=_time_series(*values))]}
    )


def test_a_region_carries_the_series_of_both_bounds_it_declares() -> None:
    lower, upper = _metric("low"), _metric("high")
    fetched = _FakeRRDFetchData(
        {
            lower: [FetchedData(performance_data=None, time_series=_time_series(1.0, 2.0, 3.0))],
            upper: [FetchedData(performance_data=None, time_series=_time_series(4.0, 5.0, 6.0))],
        }
    )

    evaluated = _evaluate(
        Region(lower=_curve(lower), upper=_curve(upper), attributes=_ATTRIBUTES), fetched
    )

    assert (evaluated.regions[0].lower, evaluated.regions[0].upper) == (
        _time_series(1.0, 2.0, 3.0),
        _time_series(4.0, 5.0, 6.0),
    )


def test_a_region_open_at_the_top_carries_no_upper_bound() -> None:
    lower = _metric("low")

    evaluated = _evaluate(
        Region(lower=_curve(lower), upper=None, attributes=_ATTRIBUTES),
        _fetched(lower, 1.0, 2.0, 3.0),
    )

    assert evaluated.regions[0].upper is None


def test_a_region_open_at_the_bottom_carries_no_lower_bound() -> None:
    upper = _metric("high")

    evaluated = _evaluate(
        Region(lower=None, upper=_curve(upper), attributes=_ATTRIBUTES),
        _fetched(upper, 1.0, 2.0, 3.0),
    )

    assert evaluated.regions[0].lower is None


def test_a_region_is_absent_when_a_bound_it_declares_is() -> None:
    evaluated = _evaluate(
        Region(lower=_curve(_metric("low")), upper=_curve(_metric("high")), attributes=_ATTRIBUTES),
        _FakeRRDFetchData(),
    )

    assert evaluated.regions == ()


def test_a_regions_bounds_are_fetched_like_any_other_drawn_curve() -> None:
    lower, upper = _metric("low"), _metric("high")

    metrics = _graph_of(
        Region(lower=_curve(lower), upper=_curve(upper), attributes=_ATTRIBUTES)
    ).metrics()

    assert set(metrics) == {lower, upper}

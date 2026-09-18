#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.graphing_engine import (
    AutoPrecision,
    Curve,
    CurveAttributes,
    DecimalNotation,
    EvaluationContext,
    FetchedData,
    HostName,
    MetricName,
    MetricProtocol,
    PredictionCurveKind,
    PredictionMetric,
    ServiceName,
    SiteID,
    TimeSeries,
    Unit,
)

from ._fixtures import _time_series, _TR

_UNIT = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))


def _prediction(curve_kind: PredictionCurveKind, valid_until: int = 86400) -> PredictionMetric:
    return PredictionMetric(
        site_id=SiteID("heute"),
        host_name=HostName("h"),
        service_name=ServiceName("svc"),
        metric_name=MetricName("util"),
        period="wday",
        valid_from=0,
        valid_until=valid_until,
        curve_kind=curve_kind,
    )


def _context(
    time_series: Mapping[PredictionMetric, TimeSeries],
) -> EvaluationContext:
    fetched: dict[MetricProtocol, Sequence[FetchedData]] = {
        metric: [FetchedData(performance_data=None, time_series=series)]
        for metric, series in time_series.items()
    }
    return EvaluationContext(fetched=fetched, time_range=_TR)


def _curve(metric: PredictionMetric) -> Curve:
    return Curve(quantity=metric, attributes=CurveAttributes(title="", unit=_UNIT, color="#000000"))


def test_a_prediction_curve_is_absent_until_it_was_fetched() -> None:
    reference = _prediction(PredictionCurveKind.UPPER_REFERENCE)

    assert reference.evaluate(_context({})) == []


def test_a_fetched_prediction_curve_draws_the_series_it_was_fetched() -> None:
    reference = _prediction(PredictionCurveKind.UPPER_REFERENCE)
    series = _time_series(1.0, 2.0, 3.0)

    assert reference.evaluate(_context({reference: series}))[0].time_series == series


def test_a_prediction_curve_reports_its_last_present_point_as_its_value() -> None:
    reference = _prediction(PredictionCurveKind.UPPER_REFERENCE)

    evaluated = reference.evaluate(_context({reference: _time_series(1.0, 3.0, None)}))

    assert evaluated[0].value == 3.0


def test_two_prediction_curves_of_one_service_are_distinct_leaves() -> None:
    assert _prediction(PredictionCurveKind.UPPER_WARNING) != _prediction(
        PredictionCurveKind.UPPER_CRITICAL
    )


def test_two_validities_of_one_prediction_are_told_apart_by_their_id() -> None:
    assert (
        _prediction(PredictionCurveKind.UPPER_WARNING).ident()
        != _prediction(PredictionCurveKind.UPPER_WARNING, valid_until=43200).ident()
    )

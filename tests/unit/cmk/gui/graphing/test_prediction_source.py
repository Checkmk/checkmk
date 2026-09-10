#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from cmk.agent_based.prediction_backend import PredictionInfo, PredictionParameters
from cmk.graphing_engine import (
    ConsolidationFunction,
    FetchedData,
    HostName,
    MetricName,
    MetricProtocol,
    PredictionCurveKind,
    PredictionMetric,
    RRDMetric,
    Service,
    ServiceName,
    SiteID,
    TimeRange,
    TimeSeries,
)
from cmk.gui.graphing._prediction_source import (
    _LivestatusPredictionSource,
    _LivestatusQuerierSource,
    _LoadedPrediction,
    _LoadedPredictions,
    _PredictionGrid,
    _PredictionKey,
    _resolved_grid,
    _sample_prediction_curves,
    Direction,
    PredictionFetchData,
)
from cmk.gui.graphing._source import PerformanceDataRow, RRDFetchTimeSeries
from cmk.utils.prediction import DataStat, PredictionData

_SITE = SiteID("heute")
_HOST = HostName("h")
_SERVICE = ServiceName("svc")
_METRIC = MetricName("util")
_PERIOD: Literal["wday"] = "wday"
_VALID_FROM = 0
_VALID_UNTIL = 86400
_RANGE = TimeRange(start=0, end=30, step=10)
_GRID = _PredictionGrid(time_range=_RANGE, num_points=3)


def _prediction(curve_kind: PredictionCurveKind, metric: MetricName = _METRIC) -> PredictionMetric:
    return PredictionMetric(
        site_id=_SITE,
        host_name=_HOST,
        service_name=_SERVICE,
        metric_name=metric,
        period=_PERIOD,
        valid_from=_VALID_FROM,
        valid_until=_VALID_UNTIL,
        curve_kind=curve_kind,
    )


def _observed() -> RRDMetric:
    return RRDMetric(
        site_id=_SITE,
        host_name=_HOST,
        service_name=_SERVICE,
        metric_name=_METRIC,
        consolidation_function=ConsolidationFunction.MAX,
    )


def _loaded(direction: Direction, *averages: float) -> _LoadedPrediction:
    return _LoadedPrediction(
        info=PredictionInfo(
            valid_interval=(_VALID_FROM, _VALID_UNTIL),
            metric=str(_METRIC),
            direction=direction,
            params=PredictionParameters(
                period=_PERIOD, horizon=90, levels=("absolute", (2.0, 4.0))
            ),
        ),
        data=PredictionData(
            points=[DataStat(average=a, min_=a, max_=a, stdev=1.0) for a in averages],
            start=_VALID_FROM,
            step=10,
        ),
    )


@dataclass
class _FakePredictionSource:
    loaded: Mapping[Direction, _LoadedPrediction]
    raises: bool = False
    unreadable: Sequence[MetricName] = ()
    calls: int = 0

    def __call__(self, keys: Sequence[_PredictionKey]) -> _LoadedPredictions:
        self.calls += 1
        if self.raises:
            raise RuntimeError("livestatus is down")
        return _LoadedPredictions(
            by_key={key: self.loaded for key in keys if key.metric_name not in self.unreadable},
            failures={
                key: RuntimeError("that file is gone")
                for key in keys
                if key.metric_name in self.unreadable
            },
        )


@dataclass
class _FakeRRDTimeSeries:
    values: Sequence[float | None] | None
    time_range: TimeRange = _RANGE

    def __call__(
        self,
        rrd_metrics: Sequence[RRDMetric],
        *,
        consolidation_function: ConsolidationFunction,  # noqa: ARG002
        time_range: TimeRange,  # noqa: ARG002
        only_site: SiteID | None,  # noqa: ARG002
    ) -> Mapping[RRDMetric, TimeSeries]:
        if self.values is None:
            return {}
        return {
            metric: TimeSeries(time_range=self.time_range, values=list(self.values))
            for metric in rrd_metrics
        }


@dataclass
class _FakeRRDPerformanceData:
    perf_data: str = "util=1"

    def __call__(
        self,
        services: Sequence[Service],
        *,
        only_site: SiteID | None,  # noqa: ARG002
    ) -> Sequence[PerformanceDataRow]:
        return [
            PerformanceDataRow(
                service=service,
                site_id=_SITE,
                perf_data=self.perf_data,
                check_command="check_mk-foo",
            )
            for service in services
        ]


def _fetch(
    metrics: Sequence[MetricProtocol],
    *,
    loaded: Mapping[Direction, _LoadedPrediction],
    observed: Sequence[float | None] | None = None,
    observed_range: TimeRange = _RANGE,
    raises: bool = False,
    unreadable: Sequence[MetricName] = (),
) -> tuple[Mapping[MetricProtocol, Sequence[FetchedData]], PredictionFetchData]:
    fetch = PredictionFetchData(
        debug=False,
        performance_data_source=_FakeRRDPerformanceData(),
        time_series_source=_FakeRRDTimeSeries(observed, observed_range),
        prediction_source=_FakePredictionSource(loaded, raises=raises, unreadable=unreadable),
    )
    return (
        fetch(metrics, consolidation_function=ConsolidationFunction.MAX, time_range=_RANGE),
        fetch,
    )


def _values(
    fetched: Mapping[MetricProtocol, Sequence[FetchedData]], metric: PredictionMetric
) -> Sequence[float | None]:
    [data] = fetched[metric]
    assert data.time_series is not None
    return data.time_series.values


def test_the_reference_curve_is_the_prediction_itself() -> None:
    reference = _prediction(PredictionCurveKind.UPPER_REFERENCE)

    fetched, _ = _fetch([reference], loaded={"upper": _loaded("upper", 0.0, 10.0, 20.0, 30.0)})

    assert _values(fetched, reference) == [10.0, 20.0, 30.0]


def test_the_level_curves_are_estimated_from_the_prediction() -> None:
    warning = _prediction(PredictionCurveKind.UPPER_WARNING)

    fetched, _ = _fetch([warning], loaded={"upper": _loaded("upper", 0.0, 10.0, 20.0, 30.0)})

    assert _values(fetched, warning) == [12.0, 22.0, 32.0]


def test_the_lower_levels_are_estimated_below_the_prediction() -> None:
    critical = _prediction(PredictionCurveKind.LOWER_CRITICAL)

    fetched, _ = _fetch([critical], loaded={"lower": _loaded("lower", 0.0, 10.0, 20.0, 30.0)})

    assert _values(fetched, critical) == [6.0, 16.0, 26.0]


def test_the_prediction_is_sampled_onto_the_grid_the_observed_series_came_back_on() -> None:
    snapped = TimeRange(start=0, end=100, step=20)
    reference = _prediction(PredictionCurveKind.UPPER_REFERENCE)

    fetched, _ = _fetch(
        [reference, _observed()],
        loaded={"upper": _loaded("upper", 1.0, 2.0, 3.0)},
        observed=[1.0, 2.0, 3.0, 4.0, 5.0],
        observed_range=snapped,
    )

    [data] = fetched[reference]
    assert data.time_series is not None
    assert (data.time_series.time_range, len(data.time_series.values)) == (snapped, 5)


def test_a_prediction_that_could_not_be_read_draws_nothing() -> None:
    reference = _prediction(PredictionCurveKind.UPPER_REFERENCE)

    fetched, _ = _fetch([reference], loaded={})

    assert reference not in fetched


def test_a_curve_of_a_direction_that_was_not_stored_draws_nothing() -> None:
    lower = _prediction(PredictionCurveKind.LOWER_WARNING)

    fetched, _ = _fetch([lower], loaded={"upper": _loaded("upper", 10.0)})

    assert lower not in fetched


def test_one_unreadable_prediction_leaves_the_others_drawn() -> None:
    readable = _prediction(PredictionCurveKind.UPPER_REFERENCE, metric=MetricName("util"))
    unreadable = _prediction(PredictionCurveKind.UPPER_REFERENCE, metric=MetricName("load1"))

    fetched, fetch = _fetch(
        [readable, unreadable],
        loaded={"upper": _loaded("upper", 0.0, 10.0, 20.0, 30.0)},
        unreadable=[MetricName("load1")],
    )

    assert (readable in fetched, unreadable in fetched) == (True, False)


def test_an_unreadable_prediction_names_the_metric_it_could_not_read() -> None:
    unreadable = _prediction(PredictionCurveKind.UPPER_REFERENCE, metric=MetricName("load1"))

    _fetched, fetch = _fetch([unreadable], loaded={}, unreadable=[MetricName("load1")])

    assert "load1" in fetch.diagnostics.errors[0]


def test_an_unreadable_prediction_is_reported_rather_than_failing_the_graph() -> None:
    _fetched, fetch = _fetch(
        [_prediction(PredictionCurveKind.UPPER_REFERENCE)], loaded={}, raises=True
    )

    assert len(fetch.diagnostics.errors) == 1


def test_a_graph_without_prediction_curves_is_fetched_as_before() -> None:
    fetched, _ = _fetch([_observed()], loaded={}, observed=[1.0, 2.0, 3.0])

    assert list(fetched) == [_observed()]


def test_the_grid_falls_back_to_the_requested_range_when_nothing_was_fetched() -> None:
    assert _resolved_grid({}, _RANGE) == _PredictionGrid(time_range=_RANGE, num_points=3)


def test_sampling_a_prediction_needs_no_fetch_at_all() -> None:
    sampled = _sample_prediction_curves({"upper": _loaded("upper", 0.0, 5.0, 6.0, 7.0)}, _GRID)

    assert sampled[PredictionCurveKind.UPPER_CRITICAL] == [9.0, 10.0, 11.0]


def test_a_prediction_is_sampled_at_the_timestamp_its_point_is_drawn_at() -> None:
    grid = _PredictionGrid(time_range=TimeRange(start=0, end=20, step=10), num_points=1)

    sampled = _sample_prediction_curves({"upper": _loaded("upper", 1.0, 2.0, 3.0)}, grid)

    assert sampled[PredictionCurveKind.UPPER_REFERENCE] == [2.0]


def test_every_predicted_metric_of_a_service_is_read_in_one_go() -> None:
    metrics = [
        _prediction(PredictionCurveKind.UPPER_REFERENCE, metric=MetricName("util")),
        _prediction(PredictionCurveKind.UPPER_REFERENCE, metric=MetricName("load1")),
    ]

    _fetched, fetch = _fetch(metrics, loaded={"upper": _loaded("upper", 1.0, 2.0, 3.0)})

    assert isinstance(fetch.prediction_source, _FakePredictionSource)
    assert fetch.prediction_source.calls == 1


def test_the_real_time_series_source_is_the_production_default() -> None:
    assert isinstance(PredictionFetchData(debug=False).time_series_source, RRDFetchTimeSeries)


def _key(service_name: ServiceName, metric: MetricName = _METRIC) -> _PredictionKey:
    return _PredictionKey(
        site_id=_SITE,
        host_name=_HOST,
        service_name=service_name,
        metric_name=metric,
        period=_PERIOD,
        valid_from=_VALID_FROM,
        valid_until=_VALID_UNTIL,
    )


@dataclass
class _FakeQuerier:
    stored: Sequence[PredictionInfo]

    def query_predicted_metrics(self) -> Sequence[str]:
        return sorted({info.metric for info in self.stored})

    def query_available_predictions(self, metric: str) -> Iterator[PredictionInfo]:
        yield from (info for info in self.stored if info.metric == metric)

    def query_prediction_data(self, meta: PredictionInfo) -> PredictionData:  # noqa: ARG002
        return PredictionData(
            points=[DataStat(average=1.0, min_=1.0, max_=1.0, stdev=1.0)],
            start=_VALID_FROM,
            step=10,
        )


@dataclass
class _FakeQuerierSource:
    stored: Sequence[PredictionInfo] = ()
    unreachable: Sequence[ServiceName] = ()

    def __call__(self, key: _PredictionKey) -> _FakeQuerier:
        if key.service_name in self.unreachable:
            raise RuntimeError("no connection to that site")
        return _FakeQuerier(self.stored)


def _stored(direction: Direction, valid_interval: tuple[int, int]) -> PredictionInfo:
    return PredictionInfo(
        valid_interval=valid_interval,
        metric=str(_METRIC),
        direction=direction,
        params=PredictionParameters(period=_PERIOD, horizon=90, levels=("absolute", (2.0, 4.0))),
    )


def test_a_service_whose_site_cannot_be_reached_loses_only_its_own_predictions() -> None:
    reachable = _key(ServiceName("reachable"))
    unreachable = _key(ServiceName("unreachable"))
    source = _LivestatusPredictionSource(
        querier_source=_FakeQuerierSource(
            stored=[_stored("upper", (_VALID_FROM, _VALID_UNTIL))],
            unreachable=[ServiceName("unreachable")],
        )
    )

    loaded = source([reachable, unreachable])

    assert (list(loaded.by_key), list(loaded.failures)) == ([reachable], [unreachable])


def test_a_service_whose_site_cannot_be_reached_reports_the_reason() -> None:
    unreachable = _key(ServiceName("unreachable"))
    source = _LivestatusPredictionSource(
        querier_source=_FakeQuerierSource(unreachable=[ServiceName("unreachable")])
    )

    loaded = source([unreachable])

    assert str(loaded.failures[unreachable]) == "no connection to that site"


def test_a_stored_prediction_of_another_validity_is_not_read_as_this_one() -> None:
    key = _key(_SERVICE)
    source = _LivestatusPredictionSource(
        querier_source=_FakeQuerierSource(
            stored=[_stored("upper", (_VALID_FROM, _VALID_UNTIL + 1))]
        )
    )

    loaded = source([key])

    assert loaded.by_key[key] == {}


def test_the_real_querier_source_is_the_production_default() -> None:
    assert isinstance(_LivestatusPredictionSource().querier_source, _LivestatusQuerierSource)

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, override, Protocol

from cmk.agent_based.prediction_backend import PredictionInfo
from cmk.ccc.hostaddress import HostName as CoreHostName
from cmk.ccc.site import SiteId
from cmk.graphing_engine import (
    ConsolidationFunction,
    FetchedData,
    HostName,
    MetricName,
    MetricProtocol,
    PredictionCurveKind,
    PredictionMetric,
    Service,
    ServiceName,
    SiteID,
    TimeRange,
    TimeSeries,
)
from cmk.gui import sites
from cmk.utils.prediction import estimate_levels, PredictionData
from cmk.utils.servicename import ServiceName as CoreServiceName

from ._prediction_query import PredictionQuerier, PredictionQuerierProtocol
from ._source import RRDFetchData

type Direction = Literal["upper", "lower"]

_CURVE_KINDS_OF: Mapping[
    Direction, tuple[PredictionCurveKind, PredictionCurveKind, PredictionCurveKind]
] = {
    "upper": (
        PredictionCurveKind.UPPER_REFERENCE,
        PredictionCurveKind.UPPER_WARNING,
        PredictionCurveKind.UPPER_CRITICAL,
    ),
    "lower": (
        PredictionCurveKind.LOWER_REFERENCE,
        PredictionCurveKind.LOWER_WARNING,
        PredictionCurveKind.LOWER_CRITICAL,
    ),
}


@dataclass(frozen=True, kw_only=True)
class _LoadedPrediction:
    info: PredictionInfo
    data: PredictionData


@dataclass(frozen=True, kw_only=True)
class _PredictionKey:
    site_id: SiteID
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    period: str
    valid_from: int
    valid_until: int


def _key_of(metric: PredictionMetric) -> _PredictionKey:
    return _PredictionKey(
        site_id=metric.site_id,
        host_name=metric.host_name,
        service_name=metric.service_name,
        metric_name=metric.metric_name,
        period=metric.period,
        valid_from=metric.valid_from,
        valid_until=metric.valid_until,
    )


def _grouped(
    predictions: Sequence[PredictionMetric],
) -> Mapping[_PredictionKey, Sequence[PredictionMetric]]:
    groups: dict[_PredictionKey, list[PredictionMetric]] = {}
    for metric in predictions:
        groups.setdefault(_key_of(metric), []).append(metric)
    return groups


def _keys_by_service(
    keys: Sequence[_PredictionKey],
) -> Mapping[Service, Sequence[_PredictionKey]]:
    by_service: dict[Service, list[_PredictionKey]] = {}
    for key in keys:
        by_service.setdefault(
            Service(site_id=key.site_id, host_name=key.host_name, service_name=key.service_name),
            [],
        ).append(key)
    return by_service


class _QuerierSourceProtocol(Protocol):
    def __call__(self, key: _PredictionKey) -> PredictionQuerierProtocol: ...


@dataclass(frozen=True)
class _LivestatusQuerierSource:
    def __call__(self, key: _PredictionKey) -> PredictionQuerierProtocol:
        return PredictionQuerier(
            livestatus_connection=sites.live().get_connection(SiteId(str(key.site_id))),
            host_name=CoreHostName(str(key.host_name)),
            service_name=CoreServiceName(str(key.service_name)),
        )


@dataclass(frozen=True, kw_only=True)
class _LoadedPredictions:
    by_key: Mapping[_PredictionKey, Mapping[Direction, _LoadedPrediction]]
    failures: Mapping[_PredictionKey, Exception]


class _PredictionSourceProtocol(Protocol):
    def __call__(self, keys: Sequence[_PredictionKey]) -> _LoadedPredictions: ...


@dataclass(frozen=True)
class _LivestatusPredictionSource:
    querier_source: _QuerierSourceProtocol = _LivestatusQuerierSource()

    def __call__(self, keys: Sequence[_PredictionKey]) -> _LoadedPredictions:
        by_key: dict[_PredictionKey, Mapping[Direction, _LoadedPrediction]] = {}
        failures: dict[_PredictionKey, Exception] = {}
        for service_keys in _keys_by_service(keys).values():
            loaded = self._of_service(service_keys)
            by_key.update(loaded.by_key)
            failures.update(loaded.failures)
        return _LoadedPredictions(by_key=by_key, failures=failures)

    def _of_service(self, keys: Sequence[_PredictionKey]) -> _LoadedPredictions:
        try:
            querier = self.querier_source(keys[0])
        except Exception as exc:
            return _LoadedPredictions(by_key={}, failures=dict.fromkeys(keys, exc))
        by_key: dict[_PredictionKey, Mapping[Direction, _LoadedPrediction]] = {}
        failures: dict[_PredictionKey, Exception] = {}
        available: dict[MetricName, Sequence[PredictionInfo]] = {}
        for key in keys:
            try:
                if key.metric_name not in available:
                    available[key.metric_name] = list(
                        querier.query_available_predictions(key.metric_name)
                    )
                by_key[key] = {
                    info.direction: _LoadedPrediction(
                        info=info, data=querier.query_prediction_data(info)
                    )
                    for info in available[key.metric_name]
                    if info.params.period == key.period
                    and info.valid_interval == (key.valid_from, key.valid_until)
                }
            except Exception as exc:
                failures[key] = exc
        return _LoadedPredictions(by_key=by_key, failures=failures)


@dataclass(frozen=True, kw_only=True)
class _PredictionGrid:
    time_range: TimeRange
    num_points: int

    def timestamps(self) -> Sequence[int]:
        return [
            self.time_range.start + (index + 1) * self.time_range.step
            for index in range(self.num_points)
        ]


def _resolved_grid(
    fetched: Mapping[MetricProtocol, Sequence[FetchedData]], time_range: TimeRange
) -> _PredictionGrid:
    for series in fetched.values():
        for data in series:
            if data.time_series is not None:
                return _PredictionGrid(
                    time_range=data.time_series.time_range,
                    num_points=len(data.time_series.values),
                )
    step = max(1, time_range.step)
    return _PredictionGrid(
        time_range=time_range, num_points=max(0, (time_range.end - time_range.start) // step)
    )


def _predict(
    prediction: _LoadedPrediction, timestamp: int
) -> tuple[float | None, float | None, float | None]:
    if (stat := prediction.data.predict(timestamp)) is None:
        return None, None, None
    levels = estimate_levels(prediction.info, stat)
    if levels is None:
        return stat.average, None, None
    return stat.average, levels[0], levels[1]


def _sample_prediction_curves(
    loaded: Mapping[Direction, _LoadedPrediction], grid: _PredictionGrid
) -> Mapping[PredictionCurveKind, Sequence[float | None]]:
    sampled: dict[PredictionCurveKind, Sequence[float | None]] = {}
    for direction, prediction in loaded.items():
        points = [_predict(prediction, timestamp) for timestamp in grid.timestamps()]
        reference_kind, warning_kind, critical_kind = _CURVE_KINDS_OF[direction]
        sampled[reference_kind] = [reference for reference, _warning, _critical in points]
        sampled[warning_kind] = [warning for _reference, warning, _critical in points]
        sampled[critical_kind] = [critical for _reference, _warning, critical in points]
    return sampled


def _values_of(
    curve_kind: PredictionCurveKind,
    sampled: Mapping[PredictionCurveKind, Sequence[float | None]],
) -> Sequence[float | None] | None:
    values = sampled.get(curve_kind)
    if values is None or all(value is None for value in values):
        return None
    return values


def _drawn_curves(
    group: Sequence[PredictionMetric],
    loaded: Mapping[Direction, _LoadedPrediction],
    grid: _PredictionGrid,
) -> Mapping[MetricProtocol, Sequence[FetchedData]]:
    if not loaded:
        return {}
    sampled = _sample_prediction_curves(loaded, grid)
    return {
        metric: [
            FetchedData(
                performance_data=None,
                time_series=TimeSeries(time_range=grid.time_range, values=list(values)),
            )
        ]
        for metric in group
        if (values := _values_of(metric.curve_kind, sampled)) is not None
    }


@dataclass(frozen=True)
class PredictionFetchData(RRDFetchData):
    prediction_source: _PredictionSourceProtocol = _LivestatusPredictionSource()

    @override
    def __call__(
        self,
        metrics: Sequence[MetricProtocol],
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
    ) -> Mapping[MetricProtocol, Sequence[FetchedData]]:
        fetched = dict(
            super().__call__(
                metrics, consolidation_function=consolidation_function, time_range=time_range
            )
        )
        predictions = [metric for metric in metrics if isinstance(metric, PredictionMetric)]
        if not predictions:
            return fetched
        grid = _resolved_grid(fetched, time_range)
        groups = _grouped(predictions)
        for key, loaded in self._load(list(groups)).items():
            fetched.update(_drawn_curves(groups[key], loaded, grid))
        return fetched

    def _load(
        self, keys: Sequence[_PredictionKey]
    ) -> Mapping[_PredictionKey, Mapping[Direction, _LoadedPrediction]]:
        try:
            loaded = self.prediction_source(keys)
        except Exception as exc:
            if self.debug:
                raise
            self.diagnostics.errors.append(f"Cannot read the stored predictions: {exc}")
            return {}
        for key, failure in loaded.failures.items():
            if self.debug:
                raise failure
            self.diagnostics.errors.append(
                f"Cannot read the prediction of {key.host_name} / {key.service_name}"
                f" / {key.metric_name}: {failure}"
            )
        return loaded.by_key

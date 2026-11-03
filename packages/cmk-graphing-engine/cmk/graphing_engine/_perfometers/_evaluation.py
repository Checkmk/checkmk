#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never, Final

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import perfometers as perfometers_v1
from cmk.graphing.v2_unstable import perfometers as perfometers_v2_unstable
from cmk.graphing_engine._data._fetched import FetchedData, PerformanceData, value_of
from cmk.graphing_engine._data._naming import MetricName
from cmk.graphing_engine._data._timeseries import TimeRange
from cmk.graphing_engine._data._units import CurveAttributes
from cmk.graphing_engine._plugins._quantity_parsing import (
    attributes_of_quantity,
    parse_quantity,
    scalar_kind_of,
)
from cmk.graphing_engine._plugins._types import (
    ApiPerfometer,
    ApiPerfometerBar,
    ApiQuantity,
    ApiScalar,
    metric_names_in_quantity,
    quantities_of_perfometer,
    scalars_in_quantity,
)
from cmk.graphing_engine._quantities._quantity import EvaluationContext, first_value
from cmk.graphing_engine._rrd._metrics import rrd_metric_of
from cmk.graphing_engine._rrd._naming import Service


class FocusBoundKind(enum.StrEnum):
    CLOSED = "closed"
    OPEN = "open"


@dataclass(frozen=True, kw_only=True)
class EvaluatedFocusBound:
    bound_kind: FocusBoundKind
    value: float


@dataclass(frozen=True, kw_only=True)
class EvaluatedFocusRange:
    lower: EvaluatedFocusBound
    upper: EvaluatedFocusBound


@dataclass(frozen=True, kw_only=True)
class EvaluatedSegment:
    value: float
    attributes: CurveAttributes


@dataclass(frozen=True, kw_only=True)
class EvaluatedPerfometer:
    name: str
    focus_range: EvaluatedFocusRange
    segments: Sequence[EvaluatedSegment]


@dataclass(frozen=True, kw_only=True)
class EvaluatedBidirectional:
    name: str
    left: EvaluatedPerfometer
    right: EvaluatedPerfometer


@dataclass(frozen=True, kw_only=True)
class EvaluatedStacked:
    name: str
    lower: EvaluatedPerfometer
    upper: EvaluatedPerfometer


type EvaluatedPerfometerLayout = EvaluatedPerfometer | EvaluatedBidirectional | EvaluatedStacked

type _ApiFocusBound = (
    perfometers_v1.Closed
    | perfometers_v1.Open
    | perfometers_v2_unstable.Closed
    | perfometers_v2_unstable.Open
)


_NO_TIME_SERIES: Final = TimeRange(start=0, end=0, step=0)


def _value_of(quantity: ApiQuantity, service: Service, context: EvaluationContext) -> float | None:
    return first_value(context.evaluate(parse_quantity(quantity, service)))


def _evaluate_focus_bound(
    bound: _ApiFocusBound, service: Service, context: EvaluationContext
) -> EvaluatedFocusBound | None:
    match bound:
        case perfometers_v1.Closed() | perfometers_v2_unstable.Closed():
            bound_kind = FocusBoundKind.CLOSED
        case perfometers_v1.Open() | perfometers_v2_unstable.Open():
            bound_kind = FocusBoundKind.OPEN
        case _:
            assert_never(bound)
    if isinstance(bound.value, int | float):
        return EvaluatedFocusBound(bound_kind=bound_kind, value=float(bound.value))
    if (value := _value_of(bound.value, service, context)) is None:
        return None
    return EvaluatedFocusBound(bound_kind=bound_kind, value=value)


def _evaluate_bar(
    bar: ApiPerfometerBar,
    service: Service,
    localizer: Callable[[str], str],
    registered_metrics: Mapping[str, metrics_v1.Metric],
    context: EvaluationContext,
) -> EvaluatedPerfometer | None:
    lower = _evaluate_focus_bound(bar.focus_range.lower, service, context)
    upper = _evaluate_focus_bound(bar.focus_range.upper, service, context)
    if lower is None or upper is None:
        return None
    segments = []
    for segment in bar.segments:
        if (value := _value_of(segment, service, context)) is None:
            return None
        segments.append(
            EvaluatedSegment(
                value=value,
                attributes=attributes_of_quantity(segment, localizer, registered_metrics),
            )
        )
    if not segments:
        return None
    return EvaluatedPerfometer(
        name=bar.name,
        focus_range=EvaluatedFocusRange(lower=lower, upper=upper),
        segments=segments,
    )


def _evaluate_plugin(
    plugin: ApiPerfometer,
    service: Service,
    localizer: Callable[[str], str],
    registered_metrics: Mapping[str, metrics_v1.Metric],
    context: EvaluationContext,
) -> EvaluatedPerfometerLayout | None:
    match plugin:
        case perfometers_v1.Perfometer() | perfometers_v2_unstable.Perfometer():
            return _evaluate_bar(plugin, service, localizer, registered_metrics, context)
        case perfometers_v1.Bidirectional() | perfometers_v2_unstable.Bidirectional():
            left = _evaluate_bar(plugin.left, service, localizer, registered_metrics, context)
            right = _evaluate_bar(plugin.right, service, localizer, registered_metrics, context)
            if left is None or right is None:
                return None
            return EvaluatedBidirectional(name=plugin.name, left=left, right=right)
        case perfometers_v1.Stacked() | perfometers_v2_unstable.Stacked():
            lower = _evaluate_bar(plugin.lower, service, localizer, registered_metrics, context)
            upper = _evaluate_bar(plugin.upper, service, localizer, registered_metrics, context)
            if lower is None or upper is None:
                return None
            return EvaluatedStacked(name=plugin.name, lower=lower, upper=upper)
        case _:
            assert_never(plugin)


@dataclass(frozen=True, kw_only=True)
class _IndexedPerfometer:
    position: int
    name: str
    plugin: ApiPerfometer
    metric_names: frozenset[MetricName]
    scalars: Sequence[ApiScalar]


def _indexed(position: int, name: str, plugin: ApiPerfometer) -> _IndexedPerfometer:
    quantities = list(quantities_of_perfometer(plugin))
    return _IndexedPerfometer(
        position=position,
        name=name,
        plugin=plugin,
        metric_names=frozenset(
            metric_name
            for quantity in quantities
            for metric_name in metric_names_in_quantity(quantity)
        ),
        scalars=[scalar for quantity in quantities for scalar in scalars_in_quantity(quantity)],
    )


def _scalar_has_a_value(
    scalar: ApiScalar, performance_data: Mapping[MetricName, PerformanceData]
) -> bool:
    data = performance_data.get(MetricName(scalar.metric_name))
    return data is not None and value_of(data, scalar_kind_of(scalar)) is not None


def _matches(
    perfometer: _IndexedPerfometer, performance_data: Mapping[MetricName, PerformanceData]
) -> bool:
    return (
        bool(perfometer.metric_names)
        and perfometer.metric_names <= performance_data.keys()
        and all(_scalar_has_a_value(scalar, performance_data) for scalar in perfometer.scalars)
    )


class PerfometerIndex:
    def __init__(self, plugins: Mapping[str, ApiPerfometer]) -> None:
        self.plugins: Final = plugins
        self._by_name: Final = {
            name: _indexed(position, name, plugin)
            for position, (name, plugin) in enumerate(plugins.items())
        }
        by_metric_name: dict[MetricName, list[_IndexedPerfometer]] = {}
        for perfometer in self._by_name.values():
            for metric_name in perfometer.metric_names:
                by_metric_name.setdefault(metric_name, []).append(perfometer)
        self._by_metric_name: Final[Mapping[MetricName, Sequence[_IndexedPerfometer]]] = (
            by_metric_name
        )

    def first_match(
        self,
        performance_data: Mapping[MetricName, PerformanceData],
        superseders: Mapping[str, str],
    ) -> ApiPerfometer | None:
        candidates = {
            perfometer.position: perfometer
            for metric_name in performance_data
            for perfometer in self._by_metric_name.get(metric_name, ())
        }
        for position in sorted(candidates):
            perfometer = candidates[position]
            if not _matches(perfometer, performance_data):
                continue
            superseder_name = superseders.get(perfometer.name)
            superseder = None if superseder_name is None else self._by_name.get(superseder_name)
            if superseder is not None and _matches(superseder, performance_data):
                return superseder.plugin
            return perfometer.plugin
        return None


def evaluate_perfometer(
    *,
    localizer: Callable[[str], str],
    service: Service,
    performance_data: Mapping[MetricName, PerformanceData],
    registered_perfometers: PerfometerIndex,
    registered_metrics: Mapping[str, metrics_v1.Metric],
    superseders: Mapping[str, str],
) -> EvaluatedPerfometerLayout | None:
    if (plugin := registered_perfometers.first_match(performance_data, superseders)) is None:
        return None
    return _evaluate_plugin(
        plugin,
        service,
        localizer,
        registered_metrics,
        EvaluationContext(
            time_range=_NO_TIME_SERIES,
            fetched={
                rrd_metric_of(service, metric_name): [
                    FetchedData(performance_data=data, time_series=None)
                ]
                for metric_name, data in performance_data.items()
            },
        ),
    )

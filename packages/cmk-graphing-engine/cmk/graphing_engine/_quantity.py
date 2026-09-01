#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from cmk.graphing.v1 import metrics as metrics_v1

from ._fetched import FetchedData, PerformanceData, SeriesAttributes
from ._naming import MetricName
from ._timeseries import TimeRange, TimeSeries
from ._units import CurveAttributes


def _last_present[T](values: Iterable[T | None]) -> T | None:
    # A fan-out leaf's series are all keyed by the same metric leaf, so a single-valued view of it
    # has to pick one: the last that carries anything at all wins.
    last: T | None = None
    for value in values:
        if value is not None:
            last = value
    return last


@dataclass(frozen=True, kw_only=True)
class EvaluationContext:
    time_range: TimeRange
    fetched: Mapping[MetricProtocol, Sequence[FetchedData]] = field(default_factory=dict)

    def fetched_of(self, metric: MetricProtocol) -> Sequence[FetchedData]:
        return self.fetched.get(metric, ())

    def data_of(self, metric: MetricProtocol) -> PerformanceData | None:
        return _last_present(data.performance_data for data in self.fetched_of(metric))

    def time_series_of(self, metric: MetricProtocol) -> TimeSeries | None:
        return _last_present(data.time_series for data in self.fetched_of(metric))


@dataclass(frozen=True, kw_only=True)
class EvaluatedQuantity:
    value: float | None
    time_series: TimeSeries
    # Per-series title macros carried by a fan-out leaf's results: substituted into the curve title
    # to tell the fanned curves apart. Empty for a single, non-fanned quantity.
    label_macros: Mapping[str, str] = field(default_factory=dict)
    # The attributes of the series this quantity was evaluated from, passed on to the curve.
    series_attributes: SeriesAttributes = field(default_factory=dict)


def first_value(results: Sequence[EvaluatedQuantity]) -> float | None:
    return results[0].value if results else None


class QuantityProtocol(Protocol):
    def kind(self) -> str: ...

    def ident(self) -> str: ...

    def metrics(self) -> Iterable[MetricProtocol]: ...

    # A quantity evaluates to a sequence of curves: empty when absent, one for an ordinary quantity,
    # and several when a fan-out leaf (e.g. a query matching many services) expands into one curve
    # per matched series.
    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]: ...

    def attributes(
        self,
        localizer: Callable[[str], str],
        registered_metrics: Mapping[str, metrics_v1.Metric],
        /,
    ) -> CurveAttributes | None: ...


# The leaves a graph fetches data for: the keys of EvaluationContext.fetched and the elements
# QuantityProtocol.metrics() yields. A metric is a quantity that draws itself, identified by its
# metric_name - that is what sets it apart from an expression node. It must be hashable: the
# evaluation context keys its fetched data by the metric leaf.
class MetricProtocol(QuantityProtocol, Hashable, Protocol):
    @property
    def metric_name(self) -> MetricName: ...


# What a drawable is bounded by: a plain number, or a quantity to be evaluated.
type Bound = int | float | QuantityProtocol


@dataclass(frozen=True, kw_only=True)
class Curve:
    """A quantity dressed for drawing: what to evaluate, and how to title, scale and colour it."""

    quantity: QuantityProtocol
    attributes: CurveAttributes
    source_id: str | None = None

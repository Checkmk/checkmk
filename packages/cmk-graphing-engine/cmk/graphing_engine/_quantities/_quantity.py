#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from cmk.graphing_engine._data._fetched import FetchedData, PerformanceData, SeriesAttributes
from cmk.graphing_engine._data._naming import MetricName
from cmk.graphing_engine._data._timeseries import last_present, TimeRange, TimeSeries


@dataclass(frozen=True, kw_only=True)
class EvaluationContext:
    time_range: TimeRange
    fetched: Mapping[MetricProtocol, Sequence[FetchedData]] = field(default_factory=dict)
    _results: dict[QuantityProtocol, Sequence[EvaluatedQuantity]] = field(
        default_factory=dict, init=False, compare=False, repr=False
    )

    def evaluate(self, quantity: QuantityProtocol) -> Sequence[EvaluatedQuantity]:
        if (results := self._results.get(quantity)) is not None:
            return results
        results = quantity.evaluate(self)
        self._results[quantity] = results
        return results

    def fetched_of(self, metric: MetricProtocol) -> Sequence[FetchedData]:
        return self.fetched.get(metric, ())

    def data_of(self, metric: MetricProtocol) -> PerformanceData | None:
        return last_present(data.performance_data for data in self.fetched_of(metric))

    def time_series_of(self, metric: MetricProtocol) -> TimeSeries | None:
        return last_present(data.time_series for data in self.fetched_of(metric))


@dataclass(frozen=True, kw_only=True)
class EvaluatedQuantity:
    value: float | None
    time_series: TimeSeries
    label_macros: Mapping[str, str] = field(default_factory=dict)
    series_attributes: SeriesAttributes = field(default_factory=dict)


def first_value(results: Sequence[EvaluatedQuantity]) -> float | None:
    return results[0].value if results else None


class QuantityProtocol(Hashable, Protocol):
    def kind(self) -> str: ...

    def ident(self) -> str: ...

    def children(self) -> Sequence[QuantityProtocol]: ...

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]: ...


@runtime_checkable
class FanOutQuantity(Protocol):
    @property
    def aggregation_kind(self) -> object | None: ...


@runtime_checkable
class MetricProtocol(QuantityProtocol, Protocol):
    @property
    def metric_name(self) -> MetricName: ...


def fetch_leaves(quantity: QuantityProtocol) -> Sequence[MetricProtocol]:
    leaves: list[MetricProtocol] = []
    walked: set[QuantityProtocol] = set()
    stack = [quantity]
    while stack:
        node = stack.pop()
        if node in walked:
            continue
        walked.add(node)
        if children := node.children():
            stack.extend(reversed(children))
        elif isinstance(node, MetricProtocol):
            leaves.append(node)
    return leaves

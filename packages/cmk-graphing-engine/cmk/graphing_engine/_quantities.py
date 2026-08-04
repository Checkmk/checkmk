#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import enum
import itertools
import math
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import assert_never, Protocol

from cmk.graphing.v1 import metrics as metrics_v1

from ._display import metric_display_attributes
from ._options import ConsolidationFunction, TimeRange
from ._perfdata import (
    constant_time_series,
    FetchedData,
    HostName,
    MetricName,
    PerformanceData,
    ServiceName,
    SiteID,
    TimeSeries,
)
from ._units import CurveAttributes


@dataclass(frozen=True, kw_only=True)
class EvaluationContext:
    time_range: TimeRange
    fetched: Mapping[MetricProtocol, Sequence[FetchedData]] = field(default_factory=dict)

    def fetched_of(self, metric: MetricProtocol) -> Sequence[FetchedData]:
        return self.fetched.get(metric, ())

    def data_of(self, metric: MetricProtocol) -> PerformanceData | None:
        performance_data: PerformanceData | None = None
        for data in self.fetched_of(metric):
            if data.performance_data is not None:
                performance_data = data.performance_data
        return performance_data

    def time_series_of(self, metric: MetricProtocol) -> TimeSeries | None:
        time_series: TimeSeries | None = None
        for data in self.fetched_of(metric):
            if data.time_series is not None:
                time_series = data.time_series
        return time_series


@dataclass(frozen=True, kw_only=True)
class EvaluatedQuantity:
    value: float | None
    time_series: TimeSeries
    # Per-series title macros carried by a fan-out leaf's results: substituted into the curve title
    # to tell the fanned curves apart. Empty for a single, non-fanned quantity.
    label_macros: Mapping[str, str] = field(default_factory=dict)


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


type _Operator = Callable[[Sequence[float | None]], float | None]


def _op_sum(point: Sequence[float | None]) -> float | None:
    return sum(value for value in point if value is not None)


def _op_product(point: Sequence[float | None]) -> float | None:
    present = [value for value in point if value is not None]
    if len(present) != len(point):
        return None
    return math.prod(present)


def _op_difference(point: Sequence[float | None]) -> float | None:
    minuend, subtrahend = point
    if minuend is None or subtrahend is None:
        return None
    return minuend - subtrahend


def _op_fraction(point: Sequence[float | None]) -> float | None:
    dividend, divisor = point
    if dividend is None or divisor is None or divisor == 0:
        return None
    return dividend / divisor


def _apply(operator: _Operator, point: Sequence[float | None]) -> float | None:
    if all(value is None for value in point):
        return None
    return operator(point)


def _operand_label_macros(operands: Sequence[EvaluatedQuantity]) -> Mapping[str, str]:
    # An operand may be a fan-out leaf that matched a single series, and then it carries that series'
    # title macros: the operation is the curve that gets drawn, so it has to carry them on.
    macros: dict[str, str] = {}
    for operand in operands:
        macros.update(operand.label_macros)
    return macros


def _apply_operator(
    operator: _Operator,
    operands: Sequence[EvaluatedQuantity],
    context: EvaluationContext,
) -> EvaluatedQuantity:
    # The scalar value and every series point run through the same _apply, so an operator's None
    # handling (Sum folds present values, Product / Difference / Fraction null on a gap) is identical
    # at both levels.
    return EvaluatedQuantity(
        value=_apply(operator, [operand.value for operand in operands]),
        time_series=TimeSeries(
            time_range=context.time_range,
            values=[
                _apply(operator, point)
                # Operands are normally on one grid, but a fetch that snapped a series differently
                # can make them differ in length. Pad the short ones rather than truncate the whole
                # curve to the shortest: a missing point is a gap, which _apply already handles.
                for point in itertools.zip_longest(
                    *(operand.time_series.values for operand in operands), fillvalue=None
                )
            ],
        ),
        label_macros=_operand_label_macros(operands),
    )


def _collapse(results: Sequence[EvaluatedQuantity]) -> EvaluatedQuantity | None:
    # An operand of an operation must be single-valued: an absent operand is None; a fan-out operand
    # (a quantity that expands into several curves) cannot take part in an operation.
    match results:
        case []:
            return None
        case [single]:
            return single
        case _:
            raise ValueError("a fan-out quantity cannot be an operand of an operation")


def _collapse_operands(
    results: Sequence[Sequence[EvaluatedQuantity]],
) -> Sequence[EvaluatedQuantity] | None:
    # An operation is absent unless it has operands and every one of them is present: an empty
    # operation and any absent operand alike make the whole operation absent (value and series). Gaps
    # within present operands are handled point-wise by _apply.
    operands = [_collapse(result) for result in results]
    present = [operand for operand in operands if operand is not None]
    if not operands or len(present) != len(operands):
        return None
    return present


@dataclass(frozen=True)
class Constant:
    value: int | float
    display: CurveAttributes | None = None

    def kind(self) -> str:
        return "constant"

    def ident(self) -> str:
        return f"{self.kind()}({self.value})"

    def metrics(self) -> Iterable[MetricProtocol]:
        return ()

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        return [
            EvaluatedQuantity(
                value=self.value, time_series=constant_time_series(self.value, context.time_range)
            )
        ]

    def attributes(
        self,
        _localizer: Callable[[str], str],
        _registered_metrics: Mapping[str, metrics_v1.Metric],
    ) -> CurveAttributes | None:
        return self.display


@dataclass(frozen=True, kw_only=True)
class RRDMetric:
    # The monitoring site the service lives on. None until resolved during the fetch; once known it
    # is part of the metric's identity, so the same host/service on two sites are distinct curves.
    site_id: SiteID | None = None
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    consolidation_function: ConsolidationFunction | None = None

    def kind(self) -> str:
        return "rrd_metric"

    def ident(self) -> str:
        location = "" if self.site_id is None else f"{self.site_id}/"
        return f"{self.kind()}({location}{self.host_name}/{self.service_name}/{self.metric_name})"

    def metrics(self) -> Iterable[MetricProtocol]:
        yield self

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        data = context.data_of(self)
        existing = context.time_series_of(self)
        if not ((data is not None and data.value is not None) or existing is not None):
            return []
        return [
            EvaluatedQuantity(
                value=None if data is None else data.value,
                time_series=(
                    existing
                    if existing is not None
                    else constant_time_series(None, context.time_range)
                ),
            )
        ]

    def attributes(
        self,
        localizer: Callable[[str], str],
        registered_metrics: Mapping[str, metrics_v1.Metric],
    ) -> CurveAttributes:
        return metric_display_attributes(self.metric_name, localizer, registered_metrics)


class ScalarKind(enum.StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"
    LOWER_WARNING = "lower_warning"
    LOWER_CRITICAL = "lower_critical"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"


@dataclass(frozen=True)
class ScalarOf:
    metric: RRDMetric
    scalar_kind: ScalarKind
    color: str | None = None

    def kind(self) -> str:
        return "scalar_of"

    def ident(self) -> str:
        return f"{self.kind()}({self.scalar_kind},{self.metric.ident()})"

    def metrics(self) -> Iterable[MetricProtocol]:
        yield self.metric

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        if (data := context.data_of(self.metric)) is None:
            return []
        match self.scalar_kind:
            case ScalarKind.WARNING:
                value = data.warning
            case ScalarKind.CRITICAL:
                value = data.critical
            case ScalarKind.LOWER_WARNING:
                value = data.lower_warning
            case ScalarKind.LOWER_CRITICAL:
                value = data.lower_critical
            case ScalarKind.MINIMUM:
                value = data.minimum
            case ScalarKind.MAXIMUM:
                value = data.maximum
            case _:
                assert_never(self.scalar_kind)
        return [
            EvaluatedQuantity(
                value=value, time_series=constant_time_series(value, context.time_range)
            )
        ]

    def attributes(
        self,
        localizer: Callable[[str], str],
        registered_metrics: Mapping[str, metrics_v1.Metric],
    ) -> CurveAttributes:
        attributes = self.metric.attributes(localizer, registered_metrics)
        label: str
        type_color: str | None
        match self.scalar_kind:
            case ScalarKind.WARNING:
                label, type_color = "Warning", "#ffd000"
            case ScalarKind.CRITICAL:
                label, type_color = "Critical", "#ff3232"
            case ScalarKind.LOWER_WARNING:
                label, type_color = "Warning (lower)", "#ffd000"
            case ScalarKind.LOWER_CRITICAL:
                label, type_color = "Critical (lower)", "#ff3232"
            case ScalarKind.MINIMUM:
                label, type_color = "Minimum", None
            case ScalarKind.MAXIMUM:
                label, type_color = "Maximum", None
            case _:
                assert_never(self.scalar_kind)
        return CurveAttributes(
            title=localizer(label),
            unit=attributes.unit,
            color=self.color or type_color or attributes.color,
        )


@dataclass(frozen=True)
class Sum:
    summands: Sequence[QuantityProtocol]
    display: CurveAttributes | None = None

    def kind(self) -> str:
        return "sum"

    def ident(self) -> str:
        return f"{self.kind()}({','.join(summand.ident() for summand in self.summands)})"

    def metrics(self) -> Iterable[MetricProtocol]:
        for summand in self.summands:
            yield from summand.metrics()

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        operands = _collapse_operands([summand.evaluate(context) for summand in self.summands])
        if operands is None:
            return []
        return [_apply_operator(_op_sum, operands, context)]

    def attributes(
        self,
        _localizer: Callable[[str], str],
        _registered_metrics: Mapping[str, metrics_v1.Metric],
    ) -> CurveAttributes | None:
        return self.display


@dataclass(frozen=True)
class Product:
    factors: Sequence[QuantityProtocol]
    display: CurveAttributes | None = None

    def kind(self) -> str:
        return "product"

    def ident(self) -> str:
        return f"{self.kind()}({','.join(factor.ident() for factor in self.factors)})"

    def metrics(self) -> Iterable[MetricProtocol]:
        for factor in self.factors:
            yield from factor.metrics()

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        operands = _collapse_operands([factor.evaluate(context) for factor in self.factors])
        if operands is None:
            return []
        return [_apply_operator(_op_product, operands, context)]

    def attributes(
        self,
        _localizer: Callable[[str], str],
        _registered_metrics: Mapping[str, metrics_v1.Metric],
    ) -> CurveAttributes | None:
        return self.display


@dataclass(frozen=True, kw_only=True)
class Difference:
    minuend: QuantityProtocol
    subtrahend: QuantityProtocol
    display: CurveAttributes | None = None

    def kind(self) -> str:
        return "difference"

    def ident(self) -> str:
        return f"{self.kind()}({self.minuend.ident()},{self.subtrahend.ident()})"

    def metrics(self) -> Iterable[MetricProtocol]:
        yield from self.minuend.metrics()
        yield from self.subtrahend.metrics()

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        operands = _collapse_operands(
            [self.minuend.evaluate(context), self.subtrahend.evaluate(context)]
        )
        if operands is None:
            return []
        return [_apply_operator(_op_difference, operands, context)]

    def attributes(
        self,
        _localizer: Callable[[str], str],
        _registered_metrics: Mapping[str, metrics_v1.Metric],
    ) -> CurveAttributes | None:
        return self.display


@dataclass(frozen=True, kw_only=True)
class Fraction:
    dividend: QuantityProtocol
    divisor: QuantityProtocol
    display: CurveAttributes | None = None

    def kind(self) -> str:
        return "fraction"

    def ident(self) -> str:
        return f"{self.kind()}({self.dividend.ident()},{self.divisor.ident()})"

    def metrics(self) -> Iterable[MetricProtocol]:
        yield from self.dividend.metrics()
        yield from self.divisor.metrics()

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        operands = _collapse_operands(
            [self.dividend.evaluate(context), self.divisor.evaluate(context)]
        )
        if operands is None:
            return []
        return [_apply_operator(_op_fraction, operands, context)]

    def attributes(
        self,
        _localizer: Callable[[str], str],
        _registered_metrics: Mapping[str, metrics_v1.Metric],
    ) -> CurveAttributes | None:
        return self.display

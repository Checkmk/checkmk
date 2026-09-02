#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import itertools
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never

from cmk.graphing.v1 import metrics as metrics_v1

from ._display import metric_display_attributes
from ._fetched import PerformanceData, SeriesAttributes
from ._naming import HostName, MetricName, Service, ServiceName, SiteID
from ._operations import (
    apply_operator,
    op_difference,
    op_fraction,
    op_product,
    op_sum,
    Operator,
)
from ._quantity import (
    EvaluatedQuantity,
    EvaluationContext,
    MetricProtocol,
    QuantityProtocol,
)
from ._timeseries import ConsolidationFunction, constant_time_series, TimeSeries
from ._units import CurveAttributes


def _operand_label_macros(operands: Sequence[EvaluatedQuantity]) -> Mapping[str, str]:
    # An operand may be a fan-out leaf that matched a single series, and then it carries that series'
    # title macros: the operation is the curve that gets drawn, so it has to carry them on.
    macros: dict[str, str] = {}
    for operand in operands:
        macros.update(operand.label_macros)
    return macros


def _operand_series_attributes(operands: Sequence[EvaluatedQuantity]) -> SeriesAttributes:
    # Same as the title macros: the operation is the drawn curve, so it carries on the attributes its
    # operands' series came with.
    attributes: dict[str, dict[str, str]] = {}
    for operand in operands:
        for kind, of_kind in operand.series_attributes.items():
            attributes.setdefault(kind, {}).update(of_kind)
    return attributes


def _apply_to_operands(
    operator: Operator,
    operands: Sequence[EvaluatedQuantity],
    context: EvaluationContext,
) -> EvaluatedQuantity:
    # The scalar value and every series point run through the same apply_operator, so an operator's None
    # handling (Sum folds present values, Product / Difference / Fraction null on a gap) is identical
    # at both levels.
    return EvaluatedQuantity(
        value=apply_operator(operator, [operand.value for operand in operands]),
        time_series=TimeSeries(
            time_range=context.time_range,
            values=[
                apply_operator(operator, point)
                # Operands are normally on one grid, but a fetch that snapped a series differently
                # can make them differ in length. Pad the short ones rather than truncate the whole
                # curve to the shortest: a missing point is a gap, which apply_operator already handles.
                for point in itertools.zip_longest(
                    *(operand.time_series.values for operand in operands), fillvalue=None
                )
            ],
        ),
        label_macros=_operand_label_macros(operands),
        series_attributes=_operand_series_attributes(operands),
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
    # within present operands are handled point-wise by apply_operator.
    operands = [_collapse(result) for result in results]
    present = [operand for operand in operands if operand is not None]
    if not operands or len(present) != len(operands):
        return None
    return present


def _operation_ident(kind: str, operands: Sequence[QuantityProtocol]) -> str:
    return f"{kind}({','.join(operand.ident() for operand in operands)})"


def _operation_metrics(operands: Sequence[QuantityProtocol]) -> Iterable[MetricProtocol]:
    for operand in operands:
        yield from operand.metrics()


def _evaluate_operation(
    operator: Operator,
    operands: Sequence[QuantityProtocol],
    context: EvaluationContext,
) -> Sequence[EvaluatedQuantity]:
    if (collapsed := _collapse_operands([o.evaluate(context) for o in operands])) is None:
        return []
    return [_apply_to_operands(operator, collapsed, context)]


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

    def service(self) -> Service:
        return Service(
            site_id=self.site_id,
            host_name=self.host_name,
            service_name=self.service_name,
        )

    def metrics(self) -> Iterable[MetricProtocol]:
        yield self

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        data = context.data_of(self)
        value = None if data is None else data.value
        existing = context.time_series_of(self)
        if value is None and existing is None:
            return []
        return [
            EvaluatedQuantity(
                value=value,
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


def rrd_metric_of(service: Service, metric_name: str) -> RRDMetric:
    return RRDMetric(
        site_id=service.site_id,
        host_name=service.host_name,
        service_name=service.service_name,
        metric_name=MetricName(metric_name),
    )


class ScalarKind(enum.StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"
    LOWER_WARNING = "lower_warning"
    LOWER_CRITICAL = "lower_critical"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"


def value_of(data: PerformanceData, scalar_kind: ScalarKind) -> float | None:
    match scalar_kind:
        case ScalarKind.WARNING:
            return data.warning
        case ScalarKind.CRITICAL:
            return data.critical
        case ScalarKind.LOWER_WARNING:
            return data.lower_warning
        case ScalarKind.LOWER_CRITICAL:
            return data.lower_critical
        case ScalarKind.MINIMUM:
            return data.minimum
        case ScalarKind.MAXIMUM:
            return data.maximum
        case _:
            assert_never(scalar_kind)


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
        value = value_of(data, self.scalar_kind)
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
        # A threshold names the metric it is a threshold of: several of them can be drawn in one
        # graph, and "Warning" alone would not say which curve it belongs to (as the legacy titles
        # spell it out too).
        label: str
        type_color: str | None
        match self.scalar_kind:
            case ScalarKind.WARNING:
                label, type_color = "Warning of %(title)s", "#ffd000"
            case ScalarKind.CRITICAL:
                label, type_color = "Critical of %(title)s", "#ff3232"
            case ScalarKind.LOWER_WARNING:
                label, type_color = "Warning (lower) of %(title)s", "#ffd000"
            case ScalarKind.LOWER_CRITICAL:
                label, type_color = "Critical (lower) of %(title)s", "#ff3232"
            case ScalarKind.MINIMUM:
                label, type_color = "Minimum of %(title)s", None
            case ScalarKind.MAXIMUM:
                label, type_color = "Maximum of %(title)s", None
            case _:
                assert_never(self.scalar_kind)
        return CurveAttributes(
            title=localizer(label) % {"title": attributes.title},
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
        return _operation_ident(self.kind(), self.summands)

    def metrics(self) -> Iterable[MetricProtocol]:
        return _operation_metrics(self.summands)

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        return _evaluate_operation(op_sum, self.summands, context)

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
        return _operation_ident(self.kind(), self.factors)

    def metrics(self) -> Iterable[MetricProtocol]:
        return _operation_metrics(self.factors)

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        return _evaluate_operation(op_product, self.factors, context)

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
        return _operation_ident(self.kind(), (self.minuend, self.subtrahend))

    def metrics(self) -> Iterable[MetricProtocol]:
        return _operation_metrics((self.minuend, self.subtrahend))

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        return _evaluate_operation(op_difference, (self.minuend, self.subtrahend), context)

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
        return _operation_ident(self.kind(), (self.dividend, self.divisor))

    def metrics(self) -> Iterable[MetricProtocol]:
        return _operation_metrics((self.dividend, self.divisor))

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        return _evaluate_operation(op_fraction, (self.dividend, self.divisor), context)

    def attributes(
        self,
        _localizer: Callable[[str], str],
        _registered_metrics: Mapping[str, metrics_v1.Metric],
    ) -> CurveAttributes | None:
        return self.display

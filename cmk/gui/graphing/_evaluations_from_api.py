#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.ccc.resulttype import Error, OK, Result
from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api

from ._graph_specification import MinimalVerticalRange
from ._translated_metrics import TranslatedMetric

type Quantity = (
    str
    | metrics_api.Constant
    | metrics_api.WarningOf
    | metrics_api.CriticalOf
    | metrics_api.MinimumOf
    | metrics_api.MaximumOf
    | metrics_api.Sum
    | metrics_api.Product
    | metrics_api.Difference
    | metrics_api.Fraction
)


@dataclass(frozen=True)
class EvaluatedQuantity:
    value: int | float


@dataclass(frozen=True, kw_only=True)
class EvaluationError:
    reason: str
    metric_name: str


def _evaluate_quantity(
    quantity: Quantity, translated_metrics: Mapping[str, TranslatedMetric]
) -> Result[EvaluatedQuantity, EvaluationError]:
    match quantity:
        case str():
            if not (translated_metric := translated_metrics.get(quantity)):
                return Error(
                    EvaluationError(
                        reason=f"No such translated metric of {quantity!r}",
                        metric_name=quantity,
                    )
                )
            return OK(
                EvaluatedQuantity(
                    translated_metric.value,
                )
            )
        case metrics_api.Constant():
            return OK(
                EvaluatedQuantity(
                    quantity.value,
                )
            )
        case metrics_api.WarningOf():
            if not (translated_metric := translated_metrics.get(quantity.metric_name)):
                return Error(
                    EvaluationError(
                        reason=f"No such translated metric of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (warn_value := translated_metric.scalar.get("warn")) is None:
                return Error(
                    EvaluationError(
                        reason=f"No such warning value of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (result := _evaluate_quantity(quantity.metric_name, translated_metrics)).is_error():
                return result
            return OK(
                EvaluatedQuantity(
                    warn_value,
                )
            )
        case metrics_api.CriticalOf():
            if not (translated_metric := translated_metrics.get(quantity.metric_name)):
                return Error(
                    EvaluationError(
                        reason=f"No such translated metric of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (crit_value := translated_metric.scalar.get("crit")) is None:
                return Error(
                    EvaluationError(
                        reason=f"No such critical value of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (result := _evaluate_quantity(quantity.metric_name, translated_metrics)).is_error():
                return result
            return OK(
                EvaluatedQuantity(
                    crit_value,
                )
            )
        case metrics_api.MinimumOf():
            if not (translated_metric := translated_metrics.get(quantity.metric_name)):
                return Error(
                    EvaluationError(
                        reason=f"No such translated metric of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (min_value := translated_metric.scalar.get("min")) is None:
                return Error(
                    EvaluationError(
                        reason=f"No such mininum value of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (result := _evaluate_quantity(quantity.metric_name, translated_metrics)).is_error():
                return result
            return OK(
                EvaluatedQuantity(
                    min_value,
                )
            )
        case metrics_api.MaximumOf():
            if not (translated_metric := translated_metrics.get(quantity.metric_name)):
                return Error(
                    EvaluationError(
                        reason=f"No such translated metric of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (max_value := translated_metric.scalar.get("max")) is None:
                return Error(
                    EvaluationError(
                        reason=f"No such maxinum value of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (result := _evaluate_quantity(quantity.metric_name, translated_metrics)).is_error():
                return result
            return OK(
                EvaluatedQuantity(
                    max_value,
                )
            )
        case metrics_api.Sum():
            results = []
            for summand in quantity.summands:
                if (result := _evaluate_quantity(summand, translated_metrics)).is_error():
                    return result
                results.append(result.ok)
            return OK(
                EvaluatedQuantity(
                    sum(r.value for r in results),
                )
            )
        case metrics_api.Product():
            results = []
            for factor in quantity.factors:
                if (result := _evaluate_quantity(factor, translated_metrics)).is_error():
                    return result
                results.append(result.ok)
            product = 1.0
            for result_ok in results:
                product *= result_ok.value
            return OK(
                EvaluatedQuantity(
                    product,
                )
            )
        case metrics_api.Difference():
            if (
                result_minuend := _evaluate_quantity(quantity.minuend, translated_metrics)
            ).is_error():
                return result_minuend
            if (
                result_subtrahend := _evaluate_quantity(quantity.subtrahend, translated_metrics)
            ).is_error():
                return result_subtrahend
            return OK(
                EvaluatedQuantity(
                    result_minuend.ok.value - result_subtrahend.ok.value,
                )
            )
        case metrics_api.Fraction():
            if (
                result_dividend := _evaluate_quantity(quantity.dividend, translated_metrics)
            ).is_error():
                return result_dividend
            if (
                result_divisor := _evaluate_quantity(quantity.divisor, translated_metrics)
            ).is_error():
                return result_divisor
            return OK(
                EvaluatedQuantity(
                    result_dividend.ok.value / result_divisor.ok.value,
                )
            )


def _evaluate_boundary(
    boundary: int | float | Quantity,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Result[int | float, EvaluationError]:
    if isinstance(boundary, int | float):
        return OK(boundary)
    if (result := _evaluate_quantity(boundary, translated_metrics)).is_error():
        return Error(result.error)
    return OK(result.ok.value)


def _evaluate_graph_range(
    graph: graphs_api.Graph,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> MinimalVerticalRange | None:
    if graph.minimal_range is None:
        return None
    return MinimalVerticalRange(
        min=(
            None
            if (r := _evaluate_boundary(graph.minimal_range.lower, translated_metrics)).is_error()
            else r.ok
        ),
        max=(
            None
            if (r := _evaluate_boundary(graph.minimal_range.upper, translated_metrics)).is_error()
            else r.ok
        ),
    )


def evaluate_graph_plugin_range(
    graph_plugin: graphs_api.Graph | graphs_api.Bidirectional,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> MinimalVerticalRange | None:
    match graph_plugin:
        case graphs_api.Graph():
            return _evaluate_graph_range(graph_plugin, translated_metrics)
        case graphs_api.Bidirectional():
            min_ranges = []
            max_ranges = []
            if lower_range := _evaluate_graph_range(graph_plugin.lower, translated_metrics):
                if lower_range.min is not None:
                    min_ranges.append(lower_range.min)
                if lower_range.max is not None:
                    max_ranges.append(lower_range.max)
            if upper_range := _evaluate_graph_range(graph_plugin.upper, translated_metrics):
                if upper_range.min is not None:
                    min_ranges.append(upper_range.min)
                if upper_range.max is not None:
                    max_ranges.append(upper_range.max)
            return (
                MinimalVerticalRange(
                    min=min(min_ranges) if min_ranges else None,
                    max=max(max_ranges) if max_ranges else None,
                )
                if min_ranges and max_ranges
                else None
            )

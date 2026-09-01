#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from cmk.ccc.hostaddress import HostName
from cmk.ccc.resulttype import Error, OK, Result
from cmk.ccc.site import SiteId
from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable
from cmk.graphing.v2_unstable import metrics as metrics_v2_unstable
from cmk.gui.color import Color, parse_color_from_api
from cmk.gui.i18n import _, translate_to_current_language
from cmk.utils.servicename import ServiceName

from ._from_api import GraphFromAPI, parse_unit_from_api, RegisteredMetric
from ._graph_metric_expressions import (
    create_graph_metric_expression_from_translated_metric,
    GraphConsolidationFunction,
    GraphMetricConstant,
    GraphMetricConstantNA,
    GraphMetricExpression,
    GraphMetricOperation,
)
from ._graph_specification import (
    GraphMetric,
)
from ._metrics import get_metric_spec
from ._translated_metrics import TranslatedMetric
from ._unit import ConvertibleUnitSpecification

type Quantity = (
    str
    | metrics_v1.Constant
    | metrics_v2_unstable.LowerWarningOf
    | metrics_v2_unstable.LowerCriticalOf
    | metrics_v1.WarningOf
    | metrics_v1.CriticalOf
    | metrics_v1.MinimumOf
    | metrics_v1.MaximumOf
    | metrics_v1.Sum
    | metrics_v1.Product
    | metrics_v1.Difference
    | metrics_v1.Fraction
)


@dataclass(frozen=True, kw_only=True)
class EvaluatedQuantity:
    title: str
    unit: ConvertibleUnitSpecification
    color: str
    value: int | float


@dataclass(frozen=True, kw_only=True)
class EvaluationError:
    reason: str
    metric_name: str


def _evaluate_quantity(
    registered_metrics: Mapping[str, RegisteredMetric],
    quantity: Quantity,
    translated_metrics: Mapping[str, TranslatedMetric],
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
                    title=get_metric_spec(quantity, registered_metrics).title,
                    unit=translated_metric.unit_spec,
                    color=translated_metric.color,
                    value=translated_metric.value,
                )
            )
        case metrics_v1.Constant():
            return OK(
                EvaluatedQuantity(
                    title=str(quantity.title.localize(translate_to_current_language)),
                    unit=parse_unit_from_api(quantity.unit),
                    color=parse_color_from_api(quantity.color).value,
                    value=quantity.value,
                )
            )
        case metrics_v2_unstable.LowerWarningOf():
            if not (translated_metric := translated_metrics.get(quantity.metric_name)):
                return Error(
                    EvaluationError(
                        reason=f"No such translated metric of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (warn_lower_value := translated_metric.scalar.warn_lower) is None:
                return Error(
                    EvaluationError(
                        reason=f"No such lower warning value of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (
                result := _evaluate_quantity(
                    registered_metrics, quantity.metric_name, translated_metrics
                )
            ).is_error():
                return result
            return OK(
                EvaluatedQuantity(
                    title=(
                        _("Warning (lower) of %(title)s")
                        % {"title": get_metric_spec(quantity.metric_name, registered_metrics).title}
                    ),
                    unit=result.ok.unit,
                    color=Color.WARN.value,
                    value=warn_lower_value,
                )
            )
        case metrics_v2_unstable.LowerCriticalOf():
            if not (translated_metric := translated_metrics.get(quantity.metric_name)):
                return Error(
                    EvaluationError(
                        reason=f"No such translated metric of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (crit_lower_value := translated_metric.scalar.crit_lower) is None:
                return Error(
                    EvaluationError(
                        reason=f"No such lower critical value of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (
                result := _evaluate_quantity(
                    registered_metrics, quantity.metric_name, translated_metrics
                )
            ).is_error():
                return result
            return OK(
                EvaluatedQuantity(
                    title=(
                        _("Critical (lower) of %(title)s")
                        % {"title": get_metric_spec(quantity.metric_name, registered_metrics).title}
                    ),
                    unit=result.ok.unit,
                    color=Color.CRIT.value,
                    value=crit_lower_value,
                )
            )
        case metrics_v1.WarningOf():
            if not (translated_metric := translated_metrics.get(quantity.metric_name)):
                return Error(
                    EvaluationError(
                        reason=f"No such translated metric of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (warn_value := translated_metric.scalar.warn) is None:
                return Error(
                    EvaluationError(
                        reason=f"No such warning value of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (
                result := _evaluate_quantity(
                    registered_metrics, quantity.metric_name, translated_metrics
                )
            ).is_error():
                return result
            return OK(
                EvaluatedQuantity(
                    title=(
                        _("Warning of %(title)s")
                        % {"title": get_metric_spec(quantity.metric_name, registered_metrics).title}
                    ),
                    unit=result.ok.unit,
                    color=Color.WARN.value,
                    value=warn_value,
                )
            )
        case metrics_v1.CriticalOf():
            if not (translated_metric := translated_metrics.get(quantity.metric_name)):
                return Error(
                    EvaluationError(
                        reason=f"No such translated metric of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (crit_value := translated_metric.scalar.crit) is None:
                return Error(
                    EvaluationError(
                        reason=f"No such critical value of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (
                result := _evaluate_quantity(
                    registered_metrics, quantity.metric_name, translated_metrics
                )
            ).is_error():
                return result
            return OK(
                EvaluatedQuantity(
                    title=(
                        _("Critical of %(title)s")
                        % {"title": get_metric_spec(quantity.metric_name, registered_metrics).title}
                    ),
                    unit=result.ok.unit,
                    color=Color.CRIT.value,
                    value=crit_value,
                )
            )
        case metrics_v1.MinimumOf():
            if not (translated_metric := translated_metrics.get(quantity.metric_name)):
                return Error(
                    EvaluationError(
                        reason=f"No such translated metric of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (min_value := translated_metric.scalar.min_) is None:
                return Error(
                    EvaluationError(
                        reason=f"No such mininum value of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (
                result := _evaluate_quantity(
                    registered_metrics, quantity.metric_name, translated_metrics
                )
            ).is_error():
                return result
            return OK(
                EvaluatedQuantity(
                    title=(
                        _("Minimum of %(title)s")
                        % {"title": get_metric_spec(quantity.metric_name, registered_metrics).title}
                    ),
                    unit=result.ok.unit,
                    color=parse_color_from_api(quantity.color).value,
                    value=min_value,
                )
            )
        case metrics_v1.MaximumOf():
            if not (translated_metric := translated_metrics.get(quantity.metric_name)):
                return Error(
                    EvaluationError(
                        reason=f"No such translated metric of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (max_value := translated_metric.scalar.max_) is None:
                return Error(
                    EvaluationError(
                        reason=f"No such maxinum value of {quantity.metric_name!r}",
                        metric_name=quantity.metric_name,
                    )
                )
            if (
                result := _evaluate_quantity(
                    registered_metrics, quantity.metric_name, translated_metrics
                )
            ).is_error():
                return result
            return OK(
                EvaluatedQuantity(
                    title=(
                        _("Maximum of %(title)s")
                        % {"title": get_metric_spec(quantity.metric_name, registered_metrics).title}
                    ),
                    unit=result.ok.unit,
                    color=parse_color_from_api(quantity.color).value,
                    value=max_value,
                )
            )
        case metrics_v1.Sum():
            results = []
            for summand in quantity.summands:
                if (
                    result := _evaluate_quantity(registered_metrics, summand, translated_metrics)
                ).is_error():
                    return result
                results.append(result.ok)
            return OK(
                EvaluatedQuantity(
                    title=str(quantity.title.localize(translate_to_current_language)),
                    unit=results[0].unit,
                    color=parse_color_from_api(quantity.color).value,
                    value=sum(r.value for r in results),
                )
            )
        case metrics_v1.Product():
            results = []
            for factor in quantity.factors:
                if (
                    result := _evaluate_quantity(registered_metrics, factor, translated_metrics)
                ).is_error():
                    return result
                results.append(result.ok)
            product = 1.0
            for result_ok in results:
                product *= result_ok.value
            return OK(
                EvaluatedQuantity(
                    title=str(quantity.title.localize(translate_to_current_language)),
                    unit=parse_unit_from_api(quantity.unit),
                    color=parse_color_from_api(quantity.color).value,
                    value=product,
                )
            )
        case metrics_v1.Difference():
            if (
                result_minuend := _evaluate_quantity(
                    registered_metrics, quantity.minuend, translated_metrics
                )
            ).is_error():
                return result_minuend
            if (
                result_subtrahend := _evaluate_quantity(
                    registered_metrics, quantity.subtrahend, translated_metrics
                )
            ).is_error():
                return result_subtrahend
            return OK(
                EvaluatedQuantity(
                    title=str(quantity.title.localize(translate_to_current_language)),
                    unit=result_minuend.ok.unit,
                    color=parse_color_from_api(quantity.color).value,
                    value=result_minuend.ok.value - result_subtrahend.ok.value,
                )
            )
        case metrics_v1.Fraction():
            if (
                result_dividend := _evaluate_quantity(
                    registered_metrics, quantity.dividend, translated_metrics
                )
            ).is_error():
                return result_dividend
            if (
                result_divisor := _evaluate_quantity(
                    registered_metrics, quantity.divisor, translated_metrics
                )
            ).is_error():
                return result_divisor
            return OK(
                EvaluatedQuantity(
                    title=str(quantity.title.localize(translate_to_current_language)),
                    unit=parse_unit_from_api(quantity.unit),
                    color=parse_color_from_api(quantity.color).value,
                    value=result_dividend.ok.value / result_divisor.ok.value,
                )
            )


def _create_quantity_id(
    quantity: Quantity, consolidation_function: GraphConsolidationFunction
) -> str:
    match quantity:
        case str():
            return f"Metric({quantity},{consolidation_function})"
        case metrics_v1.Constant():
            return f"Constant({quantity.value})"
        case metrics_v2_unstable.LowerWarningOf():
            return f"LowerWarningOf({_create_quantity_id(quantity.metric_name, consolidation_function)})"
        case metrics_v2_unstable.LowerCriticalOf():
            return f"LowerCriticalOf({_create_quantity_id(quantity.metric_name, consolidation_function)})"
        case metrics_v1.WarningOf():
            return f"WarningOf({_create_quantity_id(quantity.metric_name, consolidation_function)})"
        case metrics_v1.CriticalOf():
            return (
                f"CriticalOf({_create_quantity_id(quantity.metric_name, consolidation_function)})"
            )
        case metrics_v1.MinimumOf():
            return f"MinimumOf({_create_quantity_id(quantity.metric_name, consolidation_function)})"
        case metrics_v1.MaximumOf():
            return f"MaximumOf({_create_quantity_id(quantity.metric_name, consolidation_function)})"
        case metrics_v1.Sum():
            return f"Sum({','.join(_create_quantity_id(s, consolidation_function) for s in quantity.summands)})"
        case metrics_v1.Product():
            return f"Product({','.join(_create_quantity_id(f, consolidation_function) for f in quantity.factors)})"
        case metrics_v1.Difference():
            return f"Difference({_create_quantity_id(quantity.minuend, consolidation_function)},{_create_quantity_id(quantity.subtrahend, consolidation_function)})"
        case metrics_v1.Fraction():
            return f"Fraction({_create_quantity_id(quantity.dividend, consolidation_function)},{_create_quantity_id(quantity.divisor, consolidation_function)})"


def _is_scalar(quantity: Quantity) -> bool:
    match quantity:
        case str():
            return False
        case (
            metrics_v1.Constant()
            | metrics_v2_unstable.LowerWarningOf()
            | metrics_v2_unstable.LowerCriticalOf()
            | metrics_v1.WarningOf()
            | metrics_v1.CriticalOf()
            | metrics_v1.MinimumOf()
            | metrics_v1.MaximumOf()
        ):
            return True
        case metrics_v1.Sum():
            return all(_is_scalar(s) for s in quantity.summands)
        case metrics_v1.Product():
            return all(_is_scalar(f) for f in quantity.factors)
        case metrics_v1.Difference():
            return _is_scalar(quantity.minuend) and _is_scalar(quantity.subtrahend)
        case metrics_v1.Fraction():
            return _is_scalar(quantity.dividend) and _is_scalar(quantity.divisor)


def _to_graph_metric_expression(
    registered_metrics: Mapping[str, RegisteredMetric],
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    translated_metrics: Mapping[str, TranslatedMetric],
    consolidation_function: GraphConsolidationFunction,
    quantity: Quantity,
) -> GraphMetricExpression:
    match quantity:
        case str():
            if quantity not in translated_metrics:
                return GraphMetricConstantNA()
            return create_graph_metric_expression_from_translated_metric(
                site_id,
                host_name,
                service_name,
                translated_metrics[quantity],
                consolidation_function,
            )
        case metrics_v1.Constant():
            return GraphMetricConstant(value=float(quantity.value))
        case (
            metrics_v2_unstable.LowerWarningOf()
            | metrics_v2_unstable.LowerCriticalOf()
            | metrics_v1.WarningOf()
            | metrics_v1.CriticalOf()
            | metrics_v1.MinimumOf()
            | metrics_v1.MaximumOf()
        ):
            return (
                GraphMetricConstant(value=result.ok.value)
                if (
                    result := _evaluate_quantity(registered_metrics, quantity, translated_metrics)
                ).is_ok()
                else GraphMetricConstantNA()
            )
        case metrics_v1.Sum():
            return GraphMetricOperation(
                operator_name="+",
                operands=[
                    _to_graph_metric_expression(
                        registered_metrics,
                        site_id,
                        host_name,
                        service_name,
                        translated_metrics,
                        consolidation_function,
                        s,
                    )
                    for s in quantity.summands
                ],
            )
        case metrics_v1.Product():
            return GraphMetricOperation(
                operator_name="*",
                operands=[
                    _to_graph_metric_expression(
                        registered_metrics,
                        site_id,
                        host_name,
                        service_name,
                        translated_metrics,
                        consolidation_function,
                        f,
                    )
                    for f in quantity.factors
                ],
            )
        case metrics_v1.Difference():
            return GraphMetricOperation(
                operator_name="-",
                operands=[
                    _to_graph_metric_expression(
                        registered_metrics,
                        site_id,
                        host_name,
                        service_name,
                        translated_metrics,
                        consolidation_function,
                        quantity.minuend,
                    ),
                    _to_graph_metric_expression(
                        registered_metrics,
                        site_id,
                        host_name,
                        service_name,
                        translated_metrics,
                        consolidation_function,
                        quantity.subtrahend,
                    ),
                ],
            )
        case metrics_v1.Fraction():
            return GraphMetricOperation(
                operator_name="/",
                operands=[
                    _to_graph_metric_expression(
                        registered_metrics,
                        site_id,
                        host_name,
                        service_name,
                        translated_metrics,
                        consolidation_function,
                        quantity.dividend,
                    ),
                    _to_graph_metric_expression(
                        registered_metrics,
                        site_id,
                        host_name,
                        service_name,
                        translated_metrics,
                        consolidation_function,
                        quantity.divisor,
                    ),
                ],
            )


def _extract_metric_names(quantity: Quantity) -> Iterator[str]:
    match quantity:
        case str():
            yield quantity
        case metrics_v1.Constant():
            yield from ()
        case (
            metrics_v2_unstable.LowerWarningOf()
            | metrics_v2_unstable.LowerCriticalOf()
            | metrics_v1.WarningOf()
            | metrics_v1.CriticalOf()
            | metrics_v1.MinimumOf()
            | metrics_v1.MaximumOf()
        ):
            yield from _extract_metric_names(quantity.metric_name)
        case metrics_v1.Sum():
            for summand in quantity.summands:
                yield from _extract_metric_names(summand)
        case metrics_v1.Product():
            for factor in quantity.factors:
                yield from _extract_metric_names(factor)
        case metrics_v1.Difference():
            yield from _extract_metric_names(quantity.minuend)
            yield from _extract_metric_names(quantity.subtrahend)
        case metrics_v1.Fraction():
            yield from _extract_metric_names(quantity.dividend)
            yield from _extract_metric_names(quantity.divisor)


@dataclass(frozen=True)
class GraphMetricWithId:
    ident: str
    graph_metric: GraphMetric


@dataclass(frozen=True)
class _GraphedMetricsWithIds:
    graph_metrics: Sequence[GraphMetricWithId]
    metric_names: frozenset[str]


def _evaluate_graph_lines(
    registered_metrics: Mapping[str, RegisteredMetric],
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    consolidation_function: GraphConsolidationFunction,
    translated_metrics: Mapping[str, TranslatedMetric],
    optional: Sequence[str],
    quantities: Sequence[Quantity],
    line_type: Literal["stack", "-stack", "line", "-line"],
) -> Result[_GraphedMetricsWithIds, EvaluationError]:
    graph_metrics = []
    graphed_metric_names: set[str] = set()
    for quantity in quantities:
        if _is_scalar(quantity):
            continue
        if (
            result := _evaluate_quantity(registered_metrics, quantity, translated_metrics)
        ).is_error():
            if result.error.metric_name and result.error.metric_name in optional:
                continue
            return Error(
                EvaluationError(
                    reason=f"No such value of {quantity!r}",
                    metric_name="",
                )
            )
        graph_metrics.append(
            GraphMetricWithId(
                _create_quantity_id(quantity, consolidation_function),
                GraphMetric(
                    title=result.ok.title,
                    line_type=line_type,
                    operation=_to_graph_metric_expression(
                        registered_metrics,
                        site_id,
                        host_name,
                        service_name,
                        translated_metrics,
                        consolidation_function,
                        quantity,
                    ),
                    unit=result.ok.unit,
                    color=result.ok.color,
                ),
            )
        )
        graphed_metric_names.update(_extract_metric_names(quantity))
    return OK(_GraphedMetricsWithIds(graph_metrics, frozenset(graphed_metric_names)))


def _evaluate_predictive_metrics(
    registered_metrics: Mapping[str, RegisteredMetric],
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    consolidation_function: GraphConsolidationFunction,
    translated_metrics: Mapping[str, TranslatedMetric],
    metric_names: Sequence[str],
    line_type: Literal["line", "-line"],
) -> _GraphedMetricsWithIds:
    graph_metrics = []
    graphed_metric_names: set[str] = set()
    for metric_name in metric_names:
        for predictive_metric_name in (f"predict_{metric_name}", f"predict_lower_{metric_name}"):
            if (
                result := _evaluate_quantity(
                    registered_metrics, predictive_metric_name, translated_metrics
                )
            ).is_ok():
                graph_metrics.append(
                    GraphMetricWithId(
                        _create_quantity_id(predictive_metric_name, consolidation_function),
                        GraphMetric(
                            title=result.ok.title,
                            line_type=line_type,
                            operation=_to_graph_metric_expression(
                                registered_metrics,
                                site_id,
                                host_name,
                                service_name,
                                translated_metrics,
                                consolidation_function,
                                predictive_metric_name,
                            ),
                            unit=result.ok.unit,
                            color=result.ok.color,
                        ),
                    )
                )
                graphed_metric_names.add(predictive_metric_name)
    return _GraphedMetricsWithIds(graph_metrics, frozenset(graphed_metric_names))


def _evaluate_graph_metrics(
    registered_metrics: Mapping[str, RegisteredMetric],
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    consolidation_function: GraphConsolidationFunction,
    graph: graphs_v1.Graph | graphs_v2_unstable.Graph,
    translated_metrics: Mapping[str, TranslatedMetric],
    *,
    mirrored: bool,
) -> _GraphedMetricsWithIds:
    # Skip early on conflicting_metrics
    for var in graph.conflicting:
        if var in translated_metrics:
            return _GraphedMetricsWithIds([], frozenset())

    if (
        result_compound_lines := _evaluate_graph_lines(
            registered_metrics,
            site_id,
            host_name,
            service_name,
            consolidation_function,
            translated_metrics,
            graph.optional,
            graph.compound_lines,
            "-stack" if mirrored else "stack",
        )
    ).is_error():
        return _GraphedMetricsWithIds([], frozenset())

    if (
        result_simple_lines := _evaluate_graph_lines(
            registered_metrics,
            site_id,
            host_name,
            service_name,
            consolidation_function,
            translated_metrics,
            graph.optional,
            graph.simple_lines,
            "-line" if mirrored else "line",
        )
    ).is_error():
        return _GraphedMetricsWithIds([], frozenset())

    predictive_graphed_metrics = _evaluate_predictive_metrics(
        registered_metrics,
        site_id,
        host_name,
        service_name,
        consolidation_function,
        translated_metrics,
        sorted(
            set(result_compound_lines.ok.metric_names).union(result_simple_lines.ok.metric_names)
        ),
        "-line" if mirrored else "line",
    )

    return _GraphedMetricsWithIds(
        (
            list(result_compound_lines.ok.graph_metrics)
            + list(result_simple_lines.ok.graph_metrics)
            + list(predictive_graphed_metrics.graph_metrics)
        ),
        (
            result_compound_lines.ok.metric_names.union(result_simple_lines.ok.metric_names).union(
                predictive_graphed_metrics.metric_names
            )
        ),
    )


@dataclass(frozen=True)
class GraphedMetrics:
    graph_metrics: Sequence[GraphMetric]
    metric_names: Sequence[str]


def evaluate_graph_plugin_metrics(
    registered_metrics: Mapping[str, RegisteredMetric],
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    consolidation_function: GraphConsolidationFunction,
    graph_plugin: GraphFromAPI,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> GraphedMetrics:
    match graph_plugin:
        case graphs_v1.Graph() | graphs_v2_unstable.Graph():
            graphed_metrics = _evaluate_graph_metrics(
                registered_metrics,
                site_id,
                host_name,
                service_name,
                consolidation_function,
                graph_plugin,
                translated_metrics,
                mirrored=False,
            )
            return GraphedMetrics(
                [gmwi.graph_metric for gmwi in graphed_metrics.graph_metrics],
                sorted(graphed_metrics.metric_names),
            )
        case graphs_v1.Bidirectional() | graphs_v2_unstable.Bidirectional():
            graphed_metrics_upper = _evaluate_graph_metrics(
                registered_metrics,
                site_id,
                host_name,
                service_name,
                consolidation_function,
                graph_plugin.upper,
                translated_metrics,
                mirrored=False,
            )
            graphed_metrics_lower = _evaluate_graph_metrics(
                registered_metrics,
                site_id,
                host_name,
                service_name,
                consolidation_function,
                graph_plugin.lower,
                translated_metrics,
                mirrored=True,
            )
            return GraphedMetrics(
                (
                    [gmwi.graph_metric for gmwi in graphed_metrics_upper.graph_metrics]
                    + [gmwi.graph_metric for gmwi in graphed_metrics_lower.graph_metrics]
                ),
                sorted(
                    graphed_metrics_upper.metric_names.union(graphed_metrics_lower.metric_names)
                ),
            )

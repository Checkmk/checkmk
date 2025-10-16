#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never, Literal

from pydantic import BaseModel

from cmk.ccc.hostaddress import HostName
from cmk.ccc.resulttype import Error, OK, Result
from cmk.ccc.site import SiteId
from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api
from cmk.gui.color import parse_color_from_api, scalar_colors
from cmk.gui.i18n import _, translate_to_current_language
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.utils.servicename import ServiceName

from ._from_api import parse_unit_from_api, RegisteredMetric
from ._graph_metric_expressions import (
    create_graph_metric_expression_from_translated_metric,
    GraphConsolidationFunction,
    GraphMetricConstant,
    GraphMetricConstantNA,
    GraphMetricExpression,
    GraphMetricOperation,
)
from ._graph_specification import GraphMetric, HorizontalRule, MinimalVerticalRange
from ._metrics import get_metric_spec
from ._translated_metrics import TranslatedMetric
from ._unit import ConvertibleUnitSpecification, user_specific_unit

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
        case metrics_api.Constant():
            return OK(
                EvaluatedQuantity(
                    title=str(quantity.title.localize(translate_to_current_language)),
                    unit=parse_unit_from_api(quantity.unit),
                    color=parse_color_from_api(quantity.color),
                    value=quantity.value,
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
            if (
                result := _evaluate_quantity(
                    registered_metrics, quantity.metric_name, translated_metrics
                )
            ).is_error():
                return result
            return OK(
                EvaluatedQuantity(
                    title=(
                        _("Warning of %s")
                        % get_metric_spec(quantity.metric_name, registered_metrics).title
                    ),
                    unit=result.ok.unit,
                    color=scalar_colors["warn"],
                    value=warn_value,
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
            if (
                result := _evaluate_quantity(
                    registered_metrics, quantity.metric_name, translated_metrics
                )
            ).is_error():
                return result
            return OK(
                EvaluatedQuantity(
                    title=(
                        _("Critical of %s")
                        % get_metric_spec(quantity.metric_name, registered_metrics).title
                    ),
                    unit=result.ok.unit,
                    color=scalar_colors["crit"],
                    value=crit_value,
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
            if (
                result := _evaluate_quantity(
                    registered_metrics, quantity.metric_name, translated_metrics
                )
            ).is_error():
                return result
            return OK(
                EvaluatedQuantity(
                    title=(
                        _("Minimum of %s")
                        % get_metric_spec(quantity.metric_name, registered_metrics).title
                    ),
                    unit=result.ok.unit,
                    color=parse_color_from_api(quantity.color),
                    value=min_value,
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
            if (
                result := _evaluate_quantity(
                    registered_metrics, quantity.metric_name, translated_metrics
                )
            ).is_error():
                return result
            return OK(
                EvaluatedQuantity(
                    title=(
                        _("Maximum of %s")
                        % get_metric_spec(quantity.metric_name, registered_metrics).title
                    ),
                    unit=result.ok.unit,
                    color=parse_color_from_api(quantity.color),
                    value=max_value,
                )
            )
        case metrics_api.Sum():
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
                    color=parse_color_from_api(quantity.color),
                    value=sum(r.value for r in results),
                )
            )
        case metrics_api.Product():
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
                    color=parse_color_from_api(quantity.color),
                    value=product,
                )
            )
        case metrics_api.Difference():
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
                    color=parse_color_from_api(quantity.color),
                    value=result_minuend.ok.value - result_subtrahend.ok.value,
                )
            )
        case metrics_api.Fraction():
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
                    color=parse_color_from_api(quantity.color),
                    value=result_dividend.ok.value / result_divisor.ok.value,
                )
            )


def extract_raw_expressions_from_graph_title(title: str) -> list[str]:
    return re.findall(r"_EXPRESSION:\{.*?\}", title)


class _GraphTitleExpression(BaseModel, frozen=True):
    metric: str
    scalar: Literal["warn", "crit", "min", "max"]


def _parse_graph_title_expression(
    expression: _GraphTitleExpression,
) -> metrics_api.WarningOf | metrics_api.CriticalOf | metrics_api.MinimumOf | metrics_api.MaximumOf:
    match expression.scalar:
        case "warn":
            return metrics_api.WarningOf(expression.metric)
        case "crit":
            return metrics_api.CriticalOf(expression.metric)
        case "min":
            return metrics_api.MinimumOf(expression.metric, color=metrics_api.Color.BLACK)
        case "max":
            return metrics_api.MaximumOf(expression.metric, color=metrics_api.Color.BLACK)
        case _:
            assert_never(expression.scalar)


def evaluate_graph_plugin_title(
    registered_metrics: Mapping[str, RegisteredMetric],
    title: str,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> str:
    for raw in extract_raw_expressions_from_graph_title(title):
        if (
            result := _evaluate_quantity(
                registered_metrics,
                _parse_graph_title_expression(
                    _GraphTitleExpression.model_validate_json(raw[len("_EXPRESSION:") :]),
                ),
                translated_metrics,
            )
        ).is_ok():
            title = title.replace(
                raw,
                # rendering as an integer is hard-coded because it is all we need for now
                str(int(result.ok.value)),
                1,
            )
        else:
            return title.split("-")[0].strip()
    return title


def _evaluate_boundary(
    registered_metrics: Mapping[str, RegisteredMetric],
    boundary: int | float | Quantity,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Result[int | float, EvaluationError]:
    if isinstance(boundary, int | float):
        return OK(boundary)
    if (result := _evaluate_quantity(registered_metrics, boundary, translated_metrics)).is_error():
        return Error(result.error)
    return OK(result.ok.value)


def _evaluate_graph_range(
    registered_metrics: Mapping[str, RegisteredMetric],
    graph: graphs_api.Graph,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> MinimalVerticalRange | None:
    if graph.minimal_range is None:
        return None
    return MinimalVerticalRange(
        min=(
            None
            if (
                r := _evaluate_boundary(
                    registered_metrics, graph.minimal_range.lower, translated_metrics
                )
            ).is_error()
            else r.ok
        ),
        max=(
            None
            if (
                r := _evaluate_boundary(
                    registered_metrics, graph.minimal_range.upper, translated_metrics
                )
            ).is_error()
            else r.ok
        ),
    )


def evaluate_graph_plugin_range(
    registered_metrics: Mapping[str, RegisteredMetric],
    graph_plugin: graphs_api.Graph | graphs_api.Bidirectional,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> MinimalVerticalRange | None:
    match graph_plugin:
        case graphs_api.Graph():
            return _evaluate_graph_range(registered_metrics, graph_plugin, translated_metrics)
        case graphs_api.Bidirectional():
            min_ranges = []
            max_ranges = []
            if lower_range := _evaluate_graph_range(
                registered_metrics, graph_plugin.lower, translated_metrics
            ):
                if lower_range.min is not None:
                    min_ranges.append(lower_range.min)
                if lower_range.max is not None:
                    max_ranges.append(lower_range.max)
            if upper_range := _evaluate_graph_range(
                registered_metrics, graph_plugin.upper, translated_metrics
            ):
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


def _is_scalar(quantity: Quantity) -> bool:
    match quantity:
        case str():
            return False
        case (
            metrics_api.Constant()
            | metrics_api.WarningOf()
            | metrics_api.CriticalOf()
            | metrics_api.MinimumOf()
            | metrics_api.MaximumOf()
        ):
            return True
        case metrics_api.Sum():
            return all(_is_scalar(s) for s in quantity.summands)
        case metrics_api.Product():
            return all(_is_scalar(f) for f in quantity.factors)
        case metrics_api.Difference():
            return _is_scalar(quantity.minuend) and _is_scalar(quantity.subtrahend)
        case metrics_api.Fraction():
            return _is_scalar(quantity.dividend) and _is_scalar(quantity.divisor)


def _evaluate_graph_scalars(
    registered_metrics: Mapping[str, RegisteredMetric],
    graph: graphs_api.Graph,
    translated_metrics: Mapping[str, TranslatedMetric],
    *,
    factor: Literal[1, -1],
    temperature_unit: TemperatureUnit,
) -> Sequence[HorizontalRule]:
    horizontal_lines = []
    for quantity in list(graph.compound_lines) + list(graph.simple_lines):
        if not _is_scalar(quantity):
            continue
        if (
            result := _evaluate_quantity(registered_metrics, quantity, translated_metrics)
        ).is_error():
            # Scalar value like min and max are always optional. This makes configuration
            # of graphs easier.
            if result.error.metric_name:
                continue
            return []
        horizontal_lines.append(
            HorizontalRule(
                value=result.ok.value * factor,
                rendered_value=user_specific_unit(
                    result.ok.unit, temperature_unit
                ).formatter.render(result.ok.value),
                color=result.ok.color,
                title=result.ok.title,
            )
        )
    return horizontal_lines


def evaluate_graph_plugin_scalars(
    registered_metrics: Mapping[str, RegisteredMetric],
    graph_plugin: graphs_api.Graph | graphs_api.Bidirectional,
    translated_metrics: Mapping[str, TranslatedMetric],
    *,
    temperature_unit: TemperatureUnit,
) -> Sequence[HorizontalRule]:
    match graph_plugin:
        case graphs_api.Graph():
            return _evaluate_graph_scalars(
                registered_metrics,
                graph_plugin,
                translated_metrics,
                factor=1,
                temperature_unit=temperature_unit,
            )
        case graphs_api.Bidirectional():
            return list(
                _evaluate_graph_scalars(
                    registered_metrics,
                    graph_plugin.upper,
                    translated_metrics,
                    factor=1,
                    temperature_unit=temperature_unit,
                )
            ) + list(
                _evaluate_graph_scalars(
                    registered_metrics,
                    graph_plugin.lower,
                    translated_metrics,
                    factor=-1,
                    temperature_unit=temperature_unit,
                )
            )


def _to_graph_metric_expression(
    registered_metrics: Mapping[str, RegisteredMetric],
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    translated_metrics: Mapping[str, TranslatedMetric],
    consolidation_function: GraphConsolidationFunction | None,
    quantity: Quantity,
) -> GraphMetricExpression:
    # TODO remove duplicate eval
    match quantity:
        case str():
            return (
                create_graph_metric_expression_from_translated_metric(
                    site_id,
                    host_name,
                    service_name,
                    translated_metrics[quantity],
                    consolidation_function,
                )
                if _evaluate_quantity(registered_metrics, quantity, translated_metrics).is_ok()
                else GraphMetricConstantNA()
            )
        case metrics_api.Constant():
            return GraphMetricConstant(value=float(quantity.value))
        case (
            metrics_api.WarningOf()
            | metrics_api.CriticalOf()
            | metrics_api.MinimumOf()
            | metrics_api.MaximumOf()
        ):
            return (
                GraphMetricConstant(value=result.ok.value)
                if (
                    result := _evaluate_quantity(registered_metrics, quantity, translated_metrics)
                ).is_ok()
                else GraphMetricConstantNA()
            )
        case metrics_api.Sum():
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
        case metrics_api.Product():
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
        case metrics_api.Difference():
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
        case metrics_api.Fraction():
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
        case metrics_api.Constant():
            yield from ()
        case (
            metrics_api.WarningOf()
            | metrics_api.CriticalOf()
            | metrics_api.MinimumOf()
            | metrics_api.MaximumOf()
        ):
            yield from _extract_metric_names(quantity.metric_name)
        case metrics_api.Sum():
            for summand in quantity.summands:
                yield from _extract_metric_names(summand)
        case metrics_api.Product():
            for factor in quantity.factors:
                yield from _extract_metric_names(factor)
        case metrics_api.Difference():
            yield from _extract_metric_names(quantity.minuend)
            yield from _extract_metric_names(quantity.subtrahend)
        case metrics_api.Fraction():
            yield from _extract_metric_names(quantity.dividend)
            yield from _extract_metric_names(quantity.divisor)


@dataclass(frozen=True)
class GraphedMetrics:
    graph_metrics: Sequence[GraphMetric]
    metric_names: Sequence[str]


def _evaluate_graph_lines(
    registered_metrics: Mapping[str, RegisteredMetric],
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    translated_metrics: Mapping[str, TranslatedMetric],
    optional: Sequence[str],
    quantities: Sequence[Quantity],
    line_type: Literal["stack", "-stack", "line", "-line"],
) -> Result[GraphedMetrics, EvaluationError]:
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
            GraphMetric(
                title=result.ok.title,
                line_type=line_type,
                operation=_to_graph_metric_expression(
                    registered_metrics,
                    site_id,
                    host_name,
                    service_name,
                    translated_metrics,
                    "max",
                    quantity,
                ),
                unit=result.ok.unit,
                color=result.ok.color,
            )
        )
        graphed_metric_names.update(_extract_metric_names(quantity))
    return OK(GraphedMetrics(graph_metrics, list(graphed_metric_names)))


def _evaluate_predictive_metrics(
    registered_metrics: Mapping[str, RegisteredMetric],
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    translated_metrics: Mapping[str, TranslatedMetric],
    metric_names: Sequence[str],
    line_type: Literal["line", "-line"],
) -> tuple[Sequence[GraphMetric], set[str]]:
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
                    GraphMetric(
                        title=result.ok.title,
                        line_type=line_type,
                        operation=_to_graph_metric_expression(
                            registered_metrics,
                            site_id,
                            host_name,
                            service_name,
                            translated_metrics,
                            "max",
                            predictive_metric_name,
                        ),
                        unit=result.ok.unit,
                        color=result.ok.color,
                    )
                )
                graphed_metric_names.add(predictive_metric_name)
    return graph_metrics, graphed_metric_names


def _evaluate_graph_metrics(
    registered_metrics: Mapping[str, RegisteredMetric],
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    graph: graphs_api.Graph,
    translated_metrics: Mapping[str, TranslatedMetric],
    *,
    mirrored: bool,
) -> GraphedMetrics:
    # Skip early on conflicting_metrics
    for var in graph.conflicting:
        if var in translated_metrics:
            return GraphedMetrics([], [])

    if (
        result_compound_lines := _evaluate_graph_lines(
            registered_metrics,
            site_id,
            host_name,
            service_name,
            translated_metrics,
            graph.optional,
            graph.compound_lines,
            "-stack" if mirrored else "stack",
        )
    ).is_error():
        return GraphedMetrics([], [])

    if (
        result_simple_lines := _evaluate_graph_lines(
            registered_metrics,
            site_id,
            host_name,
            service_name,
            translated_metrics,
            graph.optional,
            graph.simple_lines,
            "-line" if mirrored else "line",
        )
    ).is_error():
        return GraphedMetrics([], [])

    predictive_graph_metrics, predictive_graphed_metrics = _evaluate_predictive_metrics(
        registered_metrics,
        site_id,
        host_name,
        service_name,
        translated_metrics,
        sorted(
            set(result_compound_lines.ok.metric_names).union(result_simple_lines.ok.metric_names)
        ),
        "-line" if mirrored else "line",
    )

    return GraphedMetrics(
        (
            list(result_compound_lines.ok.graph_metrics)
            + list(result_simple_lines.ok.graph_metrics)
            + list(predictive_graph_metrics)
        ),
        sorted(
            set(result_compound_lines.ok.metric_names)
            .union(result_simple_lines.ok.metric_names)
            .union(predictive_graphed_metrics)
        ),
    )


def evaluate_graph_plugin_metrics(
    registered_metrics: Mapping[str, RegisteredMetric],
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    graph_plugin: graphs_api.Graph | graphs_api.Bidirectional,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> GraphedMetrics:
    match graph_plugin:
        case graphs_api.Graph():
            return _evaluate_graph_metrics(
                registered_metrics,
                site_id,
                host_name,
                service_name,
                graph_plugin,
                translated_metrics,
                mirrored=False,
            )
        case graphs_api.Bidirectional():
            graphed_metrics_upper = _evaluate_graph_metrics(
                registered_metrics,
                site_id,
                host_name,
                service_name,
                graph_plugin.upper,
                translated_metrics,
                mirrored=False,
            )
            graphed_metrics_lower = _evaluate_graph_metrics(
                registered_metrics,
                site_id,
                host_name,
                service_name,
                graph_plugin.lower,
                translated_metrics,
                mirrored=True,
            )
            return GraphedMetrics(
                (
                    list(graphed_metrics_upper.graph_metrics)
                    + list(graphed_metrics_lower.graph_metrics)
                ),
                (
                    list(graphed_metrics_upper.metric_names)
                    + list(graphed_metrics_lower.metric_names)
                ),
            )

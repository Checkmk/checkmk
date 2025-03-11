#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import itertools
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never, Literal

from livestatus import SiteId

from cmk.ccc.exceptions import MKGeneralException

from cmk.utils import pnp_cleanup, regex
from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.gui.i18n import _, translate_to_current_language
from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import Row, VisualContext
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.visuals import livestatus_query_bare

from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api

from ._from_api import graphs_from_api
from ._graph_specification import (
    FixedVerticalRange,
    graph_specification_registry,
    GraphMetric,
    GraphRecipe,
    GraphSpecification,
    HorizontalRule,
    MinimalVerticalRange,
)
from ._graphs_order import GRAPHS_ORDER
from ._legacy import get_render_function, graph_info, LegacyUnitSpecification, RawGraphTemplate
from ._metric_expression import (
    Average,
    BaseMetricExpression,
    Constant,
    CriticalOf,
    Difference,
    Evaluated,
    Fraction,
    Maximum,
    Merge,
    Metric,
    MetricExpression,
    Minimum,
    parse_base_expression_from_api,
    parse_expression_from_api,
    parse_legacy_base_expression,
    parse_legacy_expression,
    parse_legacy_simple_expression,
    Product,
    Sum,
    WarningOf,
)
from ._metric_operation import (
    GraphConsolidationFunction,
    LineType,
    MetricOpConstant,
    MetricOpOperator,
    MetricOpRRDSource,
)
from ._translated_metrics import translated_metrics_from_row, TranslatedMetric
from ._unit import ConvertibleUnitSpecification
from ._utils import get_graph_data_from_livestatus


def _collect_graph_plugins() -> (
    Iterator[tuple[str, graphs_api.Graph | graphs_api.Bidirectional | RawGraphTemplate]]
):
    # TODO CMK-15246 Checkmk 2.4: Remove legacy objects
    known_plugins: set[str] = set()
    for graph in graphs_from_api.values():
        if isinstance(graph, (graphs_api.Graph, graphs_api.Bidirectional)):
            known_plugins.add(graph.name)
            yield graph.name, graph
    for template_id, template in graph_info.items():
        if template_id not in known_plugins:
            yield template_id, template


def _get_sorted_graph_plugins() -> (
    Sequence[tuple[str, graphs_api.Graph | graphs_api.Bidirectional | RawGraphTemplate]]
):
    def _by_index(graph_name: str) -> int:
        try:
            return GRAPHS_ORDER.index(graph_name)
        except ValueError:
            return -1

    return sorted(list(_collect_graph_plugins()), key=lambda t: _by_index(t[0]))


def _parse_title(template: graphs_api.Graph | graphs_api.Bidirectional | RawGraphTemplate) -> str:
    match template:
        case graphs_api.Graph() | graphs_api.Bidirectional():
            return template.title.localize(translate_to_current_language)
        case _:
            return str(template.get("title", ""))


@dataclass(frozen=True)
class GraphTemplateChoice:
    id: str
    title: str


def get_graph_template_choices() -> Sequence[GraphTemplateChoice]:
    # TODO: v.get("title", k): Use same algorithm as used in
    # GraphIdentificationTemplateBased._parse_template_metric()
    return sorted(
        [GraphTemplateChoice(p_id, _parse_title(p)) for p_id, p in _collect_graph_plugins()],
        key=lambda c: c.title,
    )


@dataclass(frozen=True, kw_only=True)
class FixedGraphTemplateRange:
    min: BaseMetricExpression
    max: BaseMetricExpression


@dataclass(frozen=True, kw_only=True)
class MinimalGraphTemplateRange:
    min: BaseMetricExpression
    max: BaseMetricExpression


def _parse_minimal_range(
    minimal_range: graphs_api.MinimalRange,
) -> MinimalGraphTemplateRange:
    return MinimalGraphTemplateRange(
        min=(
            Constant(minimal_range.lower)
            if isinstance(minimal_range.lower, (int, float))
            else parse_base_expression_from_api(minimal_range.lower)
        ),
        max=(
            Constant(minimal_range.upper)
            if isinstance(minimal_range.upper, (int, float))
            else parse_base_expression_from_api(minimal_range.upper)
        ),
    )


@dataclass(frozen=True)
class GraphTemplate:
    id: str
    title: str
    scalars: Sequence[MetricExpression]
    conflicting_metrics: Sequence[str]
    optional_metrics: Sequence[str]
    consolidation_function: GraphConsolidationFunction | None
    range: FixedGraphTemplateRange | MinimalGraphTemplateRange | None
    omit_zero_metrics: bool
    metrics: Sequence[MetricExpression]


def _parse_graph_from_api(id_: str, graph: graphs_api.Graph) -> GraphTemplate:
    metrics = [parse_expression_from_api(l, "stack") for l in graph.compound_lines]
    scalars: list[MetricExpression] = []
    for line in graph.simple_lines:
        match line:
            case (
                metrics_api.WarningOf()
                | metrics_api.CriticalOf()
                | metrics_api.MinimumOf()
                | metrics_api.MaximumOf()
            ):
                scalars.append(parse_expression_from_api(line, "line"))
            case _:
                metrics.append(parse_expression_from_api(line, "line"))
    return GraphTemplate(
        id=id_,
        title=_parse_title(graph),
        range=(None if graph.minimal_range is None else _parse_minimal_range(graph.minimal_range)),
        metrics=metrics,
        scalars=list(scalars),
        optional_metrics=graph.optional,
        conflicting_metrics=graph.conflicting,
        consolidation_function=None,
        omit_zero_metrics=False,
    )


def _parse_bidirectional_from_api(
    id_: str, bidirectional: graphs_api.Bidirectional
) -> GraphTemplate:
    ranges_min = []
    ranges_max = []
    if bidirectional.upper.minimal_range is not None:
        upper_range = _parse_minimal_range(bidirectional.upper.minimal_range)
        ranges_min.append(upper_range.min)
        ranges_max.append(upper_range.max)
    if bidirectional.lower.minimal_range is not None:
        lower_range = _parse_minimal_range(bidirectional.lower.minimal_range)
        ranges_min.append(lower_range.min)
        ranges_max.append(lower_range.max)

    metrics = [
        parse_expression_from_api(l, "stack") for l in bidirectional.upper.compound_lines
    ] + [parse_expression_from_api(l, "-stack") for l in bidirectional.lower.compound_lines]
    scalars: list[MetricExpression] = []
    for line in bidirectional.upper.simple_lines:
        match line:
            case (
                metrics_api.WarningOf()
                | metrics_api.CriticalOf()
                | metrics_api.MinimumOf()
                | metrics_api.MaximumOf()
            ):
                scalars.append(parse_expression_from_api(line, "line"))
            case _:
                metrics.append(parse_expression_from_api(line, "line"))
    for line in bidirectional.lower.simple_lines:
        match line:
            case (
                metrics_api.WarningOf()
                | metrics_api.CriticalOf()
                | metrics_api.MinimumOf()
                | metrics_api.MaximumOf()
            ):
                scalars.append(parse_expression_from_api(line, "-line"))
            case _:
                metrics.append(parse_expression_from_api(line, "-line"))
    return GraphTemplate(
        id=id_,
        title=_parse_title(bidirectional),
        range=(
            MinimalGraphTemplateRange(
                min=Minimum(ranges_min),
                max=Maximum(ranges_max),
            )
            if ranges_min and ranges_max
            else None
        ),
        metrics=metrics,
        scalars=scalars,
        optional_metrics=(list(bidirectional.lower.optional) + list(bidirectional.upper.optional)),
        conflicting_metrics=(
            list(bidirectional.lower.conflicting) + list(bidirectional.upper.conflicting)
        ),
        consolidation_function=None,
        omit_zero_metrics=False,
    )


def _parse_raw_scalar_expression(
    raw_scalar_expression: str | tuple[str, str | LazyString],
) -> MetricExpression:
    if isinstance(raw_scalar_expression, tuple):
        return parse_legacy_expression(
            raw_scalar_expression[0], "line", str(raw_scalar_expression[1]), {}
        )

    if raw_scalar_expression.endswith(":warn"):
        title = _("Warning")
    elif raw_scalar_expression.endswith(":crit"):
        title = _("Critical")
    else:
        title = raw_scalar_expression
    return parse_legacy_expression(raw_scalar_expression, "line", str(title), {})


def _parse_raw_metric_expression(
    raw_metric_expression: (
        tuple[str, LineType] | tuple[str, LineType, str] | tuple[str, LineType, LazyString]
    ),
) -> MetricExpression:
    raw_expression, line_type, *title = raw_metric_expression
    return parse_legacy_expression(raw_expression, line_type, str(title[0]) if title else "", {})


def _parse_graph_plugin(
    id_: str, template: graphs_api.Graph | graphs_api.Bidirectional | RawGraphTemplate
) -> GraphTemplate:
    match template:
        case graphs_api.Graph():
            return _parse_graph_from_api(id_, template)
        case graphs_api.Bidirectional():
            return _parse_bidirectional_from_api(id_, template)
        case _:
            return GraphTemplate(
                id=id_,
                title=_parse_title(template),
                scalars=[_parse_raw_scalar_expression(r) for r in template.get("scalars", [])],
                conflicting_metrics=template.get("conflicting_metrics", []),
                optional_metrics=template.get("optional_metrics", []),
                consolidation_function=template.get("consolidation_function"),
                range=(
                    FixedGraphTemplateRange(
                        min=parse_legacy_base_expression(template_range[0], {}),
                        max=parse_legacy_base_expression(template_range[1], {}),
                    )
                    if (template_range := template.get("range"))
                    else None
                ),
                omit_zero_metrics=template.get("omit_zero_metrics", False),
                metrics=[_parse_raw_metric_expression(r) for r in template["metrics"]],
            )


def _create_graph_template_from_name(name: str) -> GraphTemplate:
    if name.startswith("METRIC_"):
        name = name[7:]
    return GraphTemplate(
        id=f"METRIC_{name}",
        title="",
        metrics=[MetricExpression(Metric(name), line_type="area")],
        scalars=[
            MetricExpression(
                WarningOf(Metric(name)),
                line_type="line",
                title=str(_("Warning")),
            ),
            MetricExpression(
                CriticalOf(Metric(name)),
                line_type="line",
                title=str(_("Critical")),
            ),
        ],
        conflicting_metrics=[],
        optional_metrics=[],
        consolidation_function=None,
        range=None,
        omit_zero_metrics=False,
    )


def get_graph_template_from_id(template_id: str) -> GraphTemplate:
    if template_id.startswith("METRIC_"):
        return _create_graph_template_from_name(template_id)
    for id_, graph_plugin in _get_sorted_graph_plugins():
        if template_id == id_:
            return _parse_graph_plugin(id_, graph_plugin)
    raise MKGeneralException(_("There is no graph plug-in with the id '%s'") % template_id)


def evaluate_metrics(
    *,
    conflicting_metrics: Sequence[str],
    optional_metrics: Sequence[str],
    metric_expressions: Sequence[MetricExpression],
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Sequence[Evaluated]:
    # Skip early on conflicting_metrics
    for var in conflicting_metrics:
        if var in translated_metrics:
            return []
    results = []
    for metric_expression in metric_expressions:
        if (result := metric_expression.evaluate(translated_metrics)).is_error():
            if result.error.metric_name and result.error.metric_name in optional_metrics:
                continue
            return []
        results.append(result.ok)
    return results


def graph_and_single_metric_template_choices_for_metrics(
    translated_metrics: Mapping[str, TranslatedMetric],
) -> tuple[list[GraphTemplateChoice], list[GraphTemplateChoice]]:
    graph_template_choices = []
    already_graphed_metrics = set()
    for id_, graph_plugin in _get_sorted_graph_plugins():
        graph_template = _parse_graph_plugin(id_, graph_plugin)
        if evaluated_metrics := evaluate_metrics(
            conflicting_metrics=graph_template.conflicting_metrics,
            optional_metrics=graph_template.optional_metrics,
            metric_expressions=graph_template.metrics,
            translated_metrics=translated_metrics,
        ):
            graph_template_choices.append(
                GraphTemplateChoice(
                    graph_template.id,
                    graph_template.title,
                )
            )
            already_graphed_metrics.update({n for e in evaluated_metrics for n in e.metric_names()})

    single_metric_template_choices = []
    for metric_name, translated_metric in sorted(translated_metrics.items()):
        if translated_metric.auto_graph and metric_name not in already_graphed_metrics:
            single_metric_template_choices.append(
                GraphTemplateChoice(
                    f"METRIC_{metric_name}",
                    _("Metric: %s") % translated_metric.title,
                )
            )
    return graph_template_choices, single_metric_template_choices


def graph_and_single_metric_templates_choices_for_context(
    context: VisualContext,
) -> tuple[list[GraphTemplateChoice], list[GraphTemplateChoice]]:
    graph_template_choices: list[GraphTemplateChoice] = []
    single_metric_template_choices: list[GraphTemplateChoice] = []

    for row in livestatus_query_bare(
        "service",
        context,
        ["service_check_command", "service_perf_data", "service_metrics"],
    ):
        graph_template_choices_for_row, single_metric_template_choices_for_row = (
            graph_and_single_metric_template_choices_for_metrics(translated_metrics_from_row(row))
        )
        graph_template_choices.extend(graph_template_choices_for_row)
        single_metric_template_choices.extend(single_metric_template_choices_for_row)

    return graph_template_choices, single_metric_template_choices


def _to_metric_operation(
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    base_metric_expression: BaseMetricExpression,
    translated_metrics: Mapping[str, TranslatedMetric],
    consolidation_function: GraphConsolidationFunction | None,
) -> MetricOpRRDSource | MetricOpOperator | MetricOpConstant:
    match base_metric_expression:
        case Constant():
            return MetricOpConstant(value=float(base_metric_expression.value))
        case Metric():
            metrics = [
                MetricOpRRDSource(
                    site_id=site_id,
                    host_name=host_name,
                    service_name=service_name,
                    metric_name=pnp_cleanup(o.name),
                    consolidation_func_name=(
                        base_metric_expression.consolidation or consolidation_function
                    ),
                    scale=o.scale,
                )
                for o in translated_metrics[base_metric_expression.name].originals
            ]
            if len(metrics) > 1:
                return MetricOpOperator(operator_name="MERGE", operands=metrics)
            return metrics[0]
        case Sum():
            return MetricOpOperator(
                operator_name="+",
                operands=[
                    _to_metric_operation(
                        site_id,
                        host_name,
                        service_name,
                        s,
                        translated_metrics,
                        consolidation_function,
                    )
                    for s in base_metric_expression.summands
                ],
            )
        case Product():
            return MetricOpOperator(
                operator_name="*",
                operands=[
                    _to_metric_operation(
                        site_id,
                        host_name,
                        service_name,
                        f,
                        translated_metrics,
                        consolidation_function,
                    )
                    for f in base_metric_expression.factors
                ],
            )
        case Difference():
            return MetricOpOperator(
                operator_name="-",
                operands=[
                    _to_metric_operation(
                        site_id,
                        host_name,
                        service_name,
                        base_metric_expression.minuend,
                        translated_metrics,
                        consolidation_function,
                    ),
                    _to_metric_operation(
                        site_id,
                        host_name,
                        service_name,
                        base_metric_expression.subtrahend,
                        translated_metrics,
                        consolidation_function,
                    ),
                ],
            )
        case Fraction():
            return MetricOpOperator(
                operator_name="/",
                operands=[
                    _to_metric_operation(
                        site_id,
                        host_name,
                        service_name,
                        base_metric_expression.dividend,
                        translated_metrics,
                        consolidation_function,
                    ),
                    _to_metric_operation(
                        site_id,
                        host_name,
                        service_name,
                        base_metric_expression.divisor,
                        translated_metrics,
                        consolidation_function,
                    ),
                ],
            )
        case Maximum():
            return MetricOpOperator(
                operator_name="MAX",
                operands=[
                    _to_metric_operation(
                        site_id,
                        host_name,
                        service_name,
                        o,
                        translated_metrics,
                        consolidation_function,
                    )
                    for o in base_metric_expression.operands
                ],
            )
        case Minimum():
            return MetricOpOperator(
                operator_name="MIN",
                operands=[
                    _to_metric_operation(
                        site_id,
                        host_name,
                        service_name,
                        o,
                        translated_metrics,
                        consolidation_function,
                    )
                    for o in base_metric_expression.operands
                ],
            )
        case Average():
            return MetricOpOperator(
                operator_name="AVERAGE",
                operands=[
                    _to_metric_operation(
                        site_id,
                        host_name,
                        service_name,
                        o,
                        translated_metrics,
                        consolidation_function,
                    )
                    for o in base_metric_expression.operands
                ],
            )
        case Merge():
            return MetricOpOperator(
                operator_name="MERGE",
                operands=[
                    _to_metric_operation(
                        site_id,
                        host_name,
                        service_name,
                        o,
                        translated_metrics,
                        consolidation_function,
                    )
                    for o in base_metric_expression.operands
                ],
            )
        case _:
            raise TypeError(base_metric_expression)


def metric_expression_to_graph_recipe_expression(
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    base_metric_expression: BaseMetricExpression,
    translated_metrics: Mapping[str, TranslatedMetric],
    consolidation_function: GraphConsolidationFunction | None,
) -> MetricOpRRDSource | MetricOpOperator | MetricOpConstant:
    return _to_metric_operation(
        site_id,
        host_name,
        service_name,
        base_metric_expression,
        translated_metrics,
        consolidation_function,
    )


def _evaluate_graph_template_range_boundary(
    base_metric_expression: BaseMetricExpression, translated_metrics: Mapping[str, TranslatedMetric]
) -> float | None:
    if (result := base_metric_expression.evaluate(translated_metrics)).is_error():
        return None
    return result.ok.value


def evaluate_graph_template_range(
    graph_template_range: FixedGraphTemplateRange | MinimalGraphTemplateRange | None,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> FixedVerticalRange | MinimalVerticalRange | None:
    match graph_template_range:
        case FixedGraphTemplateRange(min=min_, max=max_):
            return FixedVerticalRange(
                min=_evaluate_graph_template_range_boundary(min_, translated_metrics),
                max=_evaluate_graph_template_range_boundary(max_, translated_metrics),
            )
        case MinimalGraphTemplateRange(min=min_, max=max_):
            return MinimalVerticalRange(
                min=_evaluate_graph_template_range_boundary(min_, translated_metrics),
                max=_evaluate_graph_template_range_boundary(max_, translated_metrics),
            )
        case None:
            return None
        case _:
            assert_never(graph_template_range)


def _create_graph_recipe_from_template(
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    graph_template: EvaluatedGraphTemplate,
    translated_metrics: Mapping[str, TranslatedMetric],
    specification: GraphSpecification,
) -> GraphRecipe:
    metrics = [
        GraphMetric(
            title=evaluated.title,
            line_type=evaluated.line_type,
            operation=metric_expression_to_graph_recipe_expression(
                site_id,
                host_name,
                service_name,
                evaluated.base,
                translated_metrics,
                graph_template.consolidation_function,
            ),
            unit=(
                evaluated.unit_spec
                if isinstance(evaluated.unit_spec, ConvertibleUnitSpecification)
                else evaluated.unit_spec.id
            ),
            color=evaluated.color,
        )
        for evaluated in graph_template.metrics
    ]
    units = {m.unit for m in metrics}

    # We cannot validate the hypothetical case of a mixture of metrics from the legacy and the new API
    if all(isinstance(m.unit, str) for m in metrics) or all(
        isinstance(m.unit, ConvertibleUnitSpecification) for m in metrics
    ):
        if len(units) > 1:
            raise MKGeneralException(
                _("Cannot create graph with metrics of different units '%s'")
                % ", ".join(repr(unit) for unit in units)
            )

    title = graph_template.title
    if not title:
        title = next((m.title for m in metrics), "")

    painter_options = PainterOptions.get_instance()
    if painter_options.get("show_internal_graph_and_metric_ids"):
        title = title + f" (Graph ID: {graph_template.id})"

    return GraphRecipe(
        title=title,
        metrics=metrics,
        unit_spec=(
            LegacyUnitSpecification(id=unit) if isinstance(unit := units.pop(), str) else unit
        ),
        explicit_vertical_range=evaluate_graph_template_range(
            graph_template.range,
            translated_metrics,
        ),
        horizontal_rules=[
            HorizontalRule(
                value=evaluated.value,
                rendered_value=get_render_function(evaluated.unit_spec)(evaluated.value),
                color=evaluated.color,
                title=evaluated.title,
            )
            for evaluated in graph_template.scalars
        ],
        omit_zero_metrics=graph_template.omit_zero_metrics,
        consolidation_function=graph_template.consolidation_function,
        specification=specification,
    )


def _evaluate_predictive_metrics(
    evaluated_metrics: Sequence[Evaluated],
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Iterator[Evaluated]:
    computed = set()
    for evaluated in evaluated_metrics:
        line_type: Literal["line", "-line"] = (
            "-line" if evaluated.line_type.startswith("-") else "line"
        )
        for metric_name in evaluated.metric_names():
            if metric_name in computed:
                continue
            computed.add(metric_name)
            for predictive_metric_expression in [
                MetricExpression(Metric(f"predict_{metric_name}"), line_type=line_type),
                MetricExpression(Metric(f"predict_lower_{metric_name}"), line_type=line_type),
            ]:
                if (result := predictive_metric_expression.evaluate(translated_metrics)).is_ok():
                    yield result.ok


def _evaluate_title(title: str, translated_metrics: Mapping[str, TranslatedMetric]) -> str:
    """Replace expressions in strings like CPU Load - %(load1:max@count) CPU Cores"""
    # Note: The 'CPU load' graph is the only example with such a replacement. We do not want to
    # offer such replacements in a generic way.
    reg = regex.regex(r"%\([^)]*\)")
    if m := reg.search(title):
        if (
            result := parse_legacy_simple_expression(m.group()[2:-1], translated_metrics).evaluate(
                translated_metrics
            )
        ).is_error():
            return title.split("-")[0].strip()
        return reg.sub(
            get_render_function(result.ok.unit_spec)(result.ok.value).strip(),
            title,
        )
    return title


def _evaluate_scalars(
    metric_expressions: Sequence[MetricExpression],
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Sequence[Evaluated]:
    results = []
    for metric_expression in metric_expressions:
        if (result := metric_expression.evaluate(translated_metrics)).is_error():
            # Scalar value like min and max are always optional. This makes configuration
            # of graphs easier.
            if result.error.metric_name:
                continue
            return []
        results.append(result.ok)
    return results


@dataclass(frozen=True)
class EvaluatedGraphTemplate:
    id: str
    title: str
    scalars: Sequence[Evaluated]
    consolidation_function: GraphConsolidationFunction
    range: FixedGraphTemplateRange | MinimalGraphTemplateRange | None
    omit_zero_metrics: bool
    metrics: Sequence[Evaluated]


def _create_evaluated_graph_template(
    graph_template: GraphTemplate,
    evaluated_metrics: Sequence[Evaluated],
    translated_metrics: Mapping[str, TranslatedMetric],
) -> EvaluatedGraphTemplate:
    return EvaluatedGraphTemplate(
        id=graph_template.id,
        title=_evaluate_title(graph_template.title, translated_metrics),
        scalars=_evaluate_scalars(graph_template.scalars, translated_metrics),
        consolidation_function=graph_template.consolidation_function or "max",
        range=graph_template.range,
        omit_zero_metrics=graph_template.omit_zero_metrics,
        metrics=evaluated_metrics,
    )


def _get_evaluated_graph_templates(
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Iterator[EvaluatedGraphTemplate]:
    if not translated_metrics:
        yield from ()
        return

    graph_templates = [
        _create_evaluated_graph_template(
            graph_template,
            list(
                itertools.chain(
                    evaluated_metrics,
                    _evaluate_predictive_metrics(evaluated_metrics, translated_metrics),
                )
            ),
            translated_metrics,
        )
        for id_, graph_plugin in _get_sorted_graph_plugins()
        for graph_template in [_parse_graph_plugin(id_, graph_plugin)]
        if (
            evaluated_metrics := evaluate_metrics(
                conflicting_metrics=graph_template.conflicting_metrics,
                optional_metrics=graph_template.optional_metrics,
                metric_expressions=graph_template.metrics,
                translated_metrics=translated_metrics,
            )
        )
    ]
    yield from graph_templates

    already_graphed_metrics = {
        n for t in graph_templates for e in t.metrics for n in e.metric_names()
    }
    for metric_name, translated_metric in sorted(translated_metrics.items()):
        if translated_metric.auto_graph and metric_name not in already_graphed_metrics:
            graph_template = _create_graph_template_from_name(metric_name)
            yield _create_evaluated_graph_template(
                graph_template,
                evaluate_metrics(
                    conflicting_metrics=graph_template.conflicting_metrics,
                    optional_metrics=graph_template.optional_metrics,
                    metric_expressions=graph_template.metrics,
                    translated_metrics=translated_metrics,
                ),
                translated_metrics,
            )


def _matching_graph_templates(
    *,
    graph_id: str | None,
    graph_index: int | None,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Iterable[tuple[int, EvaluatedGraphTemplate]]:
    # Performance graph dashlets already use graph_id, but for example in reports, we still use
    # graph_index. Therefore, this function needs to support both. We should switch to graph_id
    # everywhere (CMK-7308) and remove the support for graph_index. However, note that we cannot
    # easily build a corresponding transform, so even after switching to graph_id everywhere, we
    # will need to keep this functionality here for some time to support already created dashlets,
    # reports etc.
    if (
        isinstance(graph_id, str)
        and graph_id.startswith("METRIC_")
        and graph_id[7:] in translated_metrics
    ):
        # Single metrics
        graph_template = _create_graph_template_from_name(graph_id)
        yield (
            0,
            _create_evaluated_graph_template(
                graph_template,
                evaluate_metrics(
                    conflicting_metrics=graph_template.conflicting_metrics,
                    optional_metrics=graph_template.optional_metrics,
                    metric_expressions=graph_template.metrics,
                    translated_metrics=translated_metrics,
                ),
                translated_metrics,
            ),
        )
        return

    yield from (
        (index, graph_template)
        for index, graph_template in enumerate(_get_evaluated_graph_templates(translated_metrics))
        if (graph_index is None or index == graph_index)
        and (graph_id is None or graph_template.id == graph_id)
    )


class TemplateGraphSpecification(GraphSpecification, frozen=True):
    site: SiteId | None
    host_name: HostName
    service_description: ServiceName
    graph_index: int | None = None
    graph_id: str | None = None
    destination: str | None = None

    @staticmethod
    def graph_type_name() -> Literal["template"]:
        return "template"

    def _get_graph_data_from_livestatus(self) -> Row:
        return get_graph_data_from_livestatus(
            self.site,
            self.host_name,
            self.service_description,
        )

    def _build_recipe_from_template(
        self,
        *,
        graph_template: EvaluatedGraphTemplate,
        row: Row,
        translated_metrics: Mapping[str, TranslatedMetric],
        index: int,
    ) -> GraphRecipe | None:
        return _create_graph_recipe_from_template(
            row["site"],
            row["host_name"],
            row.get("service_description", "_HOST_"),
            graph_template,
            translated_metrics,
            specification=type(self)(
                site=self.site,
                host_name=self.host_name,
                service_description=self.service_description,
                destination=self.destination,
                graph_index=index,
                graph_id=graph_template.id,
            ),
        )

    def recipes(self) -> list[GraphRecipe]:
        row = self._get_graph_data_from_livestatus()
        translated_metrics = translated_metrics_from_row(row)
        return [
            recipe
            for index, graph_template in _matching_graph_templates(
                graph_id=self.graph_id,
                graph_index=self.graph_index,
                translated_metrics=translated_metrics,
            )
            if (
                recipe := self._build_recipe_from_template(
                    graph_template=graph_template,
                    row=row,
                    translated_metrics=translated_metrics,
                    index=index,
                )
            )
        ]


def get_template_graph_specification(
    *,
    site_id: SiteId | None,
    host_name: HostName,
    service_name: ServiceName,
    graph_index: int | None = None,
    graph_id: str | None = None,
    destination: str | None = None,
) -> TemplateGraphSpecification:
    if issubclass(
        graph_specification := graph_specification_registry["template"], TemplateGraphSpecification
    ):
        return graph_specification(
            site=site_id,
            host_name=host_name,
            service_description=service_name,
            graph_index=graph_index,
            graph_id=graph_id,
            destination=destination,
        )
    raise TypeError(graph_specification)

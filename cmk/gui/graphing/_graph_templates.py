#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never, ClassVar, Literal

from livestatus import SiteId

from cmk.ccc.exceptions import MKGeneralException

from cmk.utils import pnp_cleanup, regex
from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.gui.i18n import _, translate_to_current_language
from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import Row
from cmk.gui.utils.speaklater import LazyString

from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api

from ._expression import (
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
from ._from_api import graphs_from_api
from ._graph_specification import (
    FixedVerticalRange,
    GraphMetric,
    GraphRecipe,
    GraphSpecification,
    HorizontalRule,
    MetricOpConstant,
    MetricOpOperator,
    MetricOpRRDSource,
    MinimalVerticalRange,
)
from ._legacy import get_render_function, graph_info, LegacyUnitSpecification, RawGraphTemplate
from ._translated_metrics import translated_metrics_from_row, TranslatedMetric
from ._type_defs import GraphConsolidationFunction, LineType
from ._unit import ConvertibleUnitSpecification
from ._utils import get_graph_data_from_livestatus


def _graph_templates_from_plugins() -> (
    Iterator[tuple[str, graphs_api.Graph | graphs_api.Bidirectional | RawGraphTemplate]]
):
    # TODO CMK-15246 Checkmk 2.4: Remove legacy objects
    known_graph_templates: set[str] = set()
    for graph in graphs_from_api.values():
        if isinstance(graph, (graphs_api.Graph, graphs_api.Bidirectional)):
            known_graph_templates.add(graph.name)
            yield graph.name, graph
    for template_id, template in graph_info.items():
        if template_id not in known_graph_templates:
            yield template_id, template


def _parse_title(template: graphs_api.Graph | graphs_api.Bidirectional | RawGraphTemplate) -> str:
    match template:
        case graphs_api.Graph() | graphs_api.Bidirectional():
            return template.title.localize(translate_to_current_language)
        case _:
            return str(template.get("title", ""))


def get_graph_template_choices() -> list[tuple[str, str]]:
    # TODO: v.get("title", k): Use same algorithm as used in
    # GraphIdentificationTemplateBased._parse_template_metric()
    return sorted(
        [(t_id, _parse_title(t)) for t_id, t in _graph_templates_from_plugins()],
        key=lambda k_v: k_v[1],
    )


@dataclass(frozen=True)
class MetricUnitColor:
    unit: str | ConvertibleUnitSpecification
    color: str


def compute_title(
    metric_expression: MetricExpression, translated_metrics: Mapping[str, TranslatedMetric]
) -> str:
    if metric_expression.title:
        return metric_expression.title
    return translated_metrics[next(metric_expression.metric_names())].title


def compute_unit_color(
    metric_expression: MetricExpression,
    translated_metrics: Mapping[str, TranslatedMetric],
    optional_metrics: Sequence[str],
) -> MetricUnitColor | None:
    if (result := metric_expression.evaluate(translated_metrics)).is_error():
        if result.error.metric_name and result.error.metric_name in optional_metrics:
            return None
        raise MKGeneralException(
            _("Graph recipe '%s' has the error '%s', available are: %s")
            % (
                metric_expression,
                result.error.reason,
                ", ".join(sorted(translated_metrics.keys())) or "None",
            )
        )
    return MetricUnitColor(
        (
            result.ok.unit_spec
            if isinstance(result.ok.unit_spec, ConvertibleUnitSpecification)
            else result.ok.unit_spec.id
        ),
        result.ok.color,
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


def _graph_template_from_api_graph(id_: str, graph: graphs_api.Graph) -> GraphTemplate:
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


def _graph_template_from_api_bidirectional(
    id_: str, bidirectional: graphs_api.Bidirectional
) -> GraphTemplate:
    ranges_min = []
    ranges_max = []
    if bidirectional.lower.minimal_range is not None:
        lower_range = _parse_minimal_range(bidirectional.lower.minimal_range)
        ranges_min.append(lower_range.min)
        ranges_max.append(lower_range.max)
    if bidirectional.upper.minimal_range is not None:
        upper_range = _parse_minimal_range(bidirectional.upper.minimal_range)
        ranges_min.append(upper_range.min)
        ranges_max.append(upper_range.max)

    metrics = [
        parse_expression_from_api(l, "-stack") for l in bidirectional.lower.compound_lines
    ] + [parse_expression_from_api(l, "stack") for l in bidirectional.upper.compound_lines]
    scalars: list[MetricExpression] = []
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


def _parse_raw_graph_range(raw_graph_range: tuple[int | str, int | str]) -> FixedGraphTemplateRange:
    return FixedGraphTemplateRange(
        min=parse_legacy_base_expression(raw_graph_range[0], {}),
        max=parse_legacy_base_expression(raw_graph_range[1], {}),
    )


def _parse_raw_metric_expression(
    raw_metric_expression: (
        tuple[str, LineType] | tuple[str, LineType, str] | tuple[str, LineType, LazyString]
    ),
) -> MetricExpression:
    raw_expression, line_type, *title = raw_metric_expression
    return parse_legacy_expression(raw_expression, line_type, str(title[0]) if title else "", {})


def _parse_graph_template(
    id_: str, template: graphs_api.Graph | graphs_api.Bidirectional | RawGraphTemplate
) -> GraphTemplate:
    match template:
        case graphs_api.Graph():
            return _graph_template_from_api_graph(id_, template)
        case graphs_api.Bidirectional():
            return _graph_template_from_api_bidirectional(id_, template)
        case _:
            return GraphTemplate(
                id=id_,
                title=_parse_title(template),
                scalars=[_parse_raw_scalar_expression(r) for r in template.get("scalars", [])],
                conflicting_metrics=template.get("conflicting_metrics", []),
                optional_metrics=template.get("optional_metrics", []),
                consolidation_function=template.get("consolidation_function"),
                range=(
                    _parse_raw_graph_range(template_range)
                    if (template_range := template.get("range"))
                    else None
                ),
                omit_zero_metrics=template.get("omit_zero_metrics", False),
                metrics=[_parse_raw_metric_expression(r) for r in template["metrics"]],
            )


def graph_template_from_name(name: str) -> GraphTemplate:
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


def get_graph_template(template_id: str) -> GraphTemplate:
    if template_id.startswith("METRIC_"):
        return graph_template_from_name(template_id)
    for id_, template in _graph_templates_from_plugins():
        if template_id == id_:
            return _parse_graph_template(id_, template)
    raise MKGeneralException(_("There is no graph template with the id '%s'") % template_id)


def _compute_predictive_metrics(
    translated_metrics: Mapping[str, TranslatedMetric], metrics: Sequence[MetricExpression]
) -> Iterator[MetricExpression]:
    for metric_expression in metrics:
        line_type: Literal["line", "-line"] = (
            "-line" if metric_expression.line_type.startswith("-") else "line"
        )
        for metric_name in metric_expression.metric_names():
            if (predict_metric_name := f"predict_{metric_name}") in translated_metrics:
                yield MetricExpression(Metric(predict_metric_name), line_type=line_type)
            if (predict_lower_metric_name := f"predict_lower_{metric_name}") in translated_metrics:
                yield MetricExpression(Metric(predict_lower_metric_name), line_type=line_type)


def applicable_metrics(
    graph_template: GraphTemplate,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Sequence[tuple[MetricExpression, Evaluated]]:
    # Skip early on conflicting_metrics
    for var in graph_template.conflicting_metrics:
        if var in translated_metrics:
            return []

    results = []
    for metric_expression in graph_template.metrics:
        if (result := metric_expression.evaluate(translated_metrics)).is_error():
            if (
                result.error.metric_name
                and result.error.metric_name in graph_template.optional_metrics
            ):
                continue
            return []
        results.append((metric_expression, result.ok))
    return results


def get_graph_templates(
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Iterator[GraphTemplate]:
    if not translated_metrics:
        yield from ()
        return

    graph_templates = [
        GraphTemplate(
            id=graph_template.id,
            title=graph_template.title,
            scalars=graph_template.scalars,
            conflicting_metrics=graph_template.conflicting_metrics,
            optional_metrics=graph_template.optional_metrics,
            consolidation_function=graph_template.consolidation_function,
            range=graph_template.range,
            omit_zero_metrics=graph_template.omit_zero_metrics,
            metrics=(
                list(metrics) + list(_compute_predictive_metrics(translated_metrics, metrics))
            ),
        )
        for id_, template in _graph_templates_from_plugins()
        for graph_template in (_parse_graph_template(id_, template),)
        if (metrics := [m for m, _e in applicable_metrics(graph_template, translated_metrics)])
    ]
    yield from graph_templates

    already_graphed_metrics = {
        n for gt in graph_templates for me in gt.metrics for n in me.metric_names()
    }
    for metric_name, translated_metric in sorted(translated_metrics.items()):
        if translated_metric.auto_graph and metric_name not in already_graphed_metrics:
            yield graph_template_from_name(metric_name)


class TemplateGraphSpecification(GraphSpecification, frozen=True):
    # Overwritten in cmk/gui/graphing/cee/__init__.py
    TUNE_GRAPH_TEMPLATE: ClassVar[
        Callable[[GraphTemplate, TemplateGraphSpecification], GraphTemplate | None]
    ] = lambda graph_template, _spec: graph_template

    site: SiteId | None
    host_name: HostName
    service_description: ServiceName
    graph_index: int | None = None
    graph_id: str | None = None
    destination: str | None = None

    @staticmethod
    def graph_type_name() -> Literal["template"]:
        return "template"

    def recipes(self) -> list[GraphRecipe]:
        row = get_graph_data_from_livestatus(self.site, self.host_name, self.service_description)
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

    def _build_recipe_from_template(
        self,
        *,
        graph_template: GraphTemplate,
        row: Row,
        translated_metrics: Mapping[str, TranslatedMetric],
        index: int,
    ) -> GraphRecipe | None:
        if not (
            graph_template_tuned := TemplateGraphSpecification.TUNE_GRAPH_TEMPLATE(
                graph_template,
                self,
            )
        ):
            return None

        return create_graph_recipe_from_template(
            row["site"],
            row["host_name"],
            row.get("service_description", "_HOST_"),
            graph_template_tuned,
            translated_metrics,
            specification=TemplateGraphSpecification(
                site=self.site,
                host_name=self.host_name,
                service_description=self.service_description,
                destination=self.destination,
                # Performance graph dashlets already use graph_id, but for example in reports, we still
                # use graph_index. We should switch to graph_id everywhere (CMK-7308). Once this is
                # done, we can remove the line below.
                graph_index=index,
                graph_id=graph_template_tuned.id,
            ),
        )


# Performance graph dashlets already use graph_id, but for example in reports, we still use
# graph_index. Therefore, this function needs to support both. We should switch to graph_id
# everywhere (CMK-7308) and remove the support for graph_index. However, note that we cannot easily
# build a corresponding transform, so even after switching to graph_id everywhere, we will need to
# keep this functionality here for some time to support already created dashlets, reports etc.
def _matching_graph_templates(
    *,
    graph_id: str | None,
    graph_index: int | None,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Iterable[tuple[int, GraphTemplate]]:
    # Single metrics
    if (
        isinstance(graph_id, str)
        and graph_id.startswith("METRIC_")
        and graph_id[7:] in translated_metrics
    ):
        yield (0, graph_template_from_name(graph_id))
        return

    yield from (
        (index, graph_template)
        for index, graph_template in enumerate(get_graph_templates(translated_metrics))
        if (graph_index is None or index == graph_index)
        and (graph_id is None or graph_template.id == graph_id)
    )


def _replace_expressions(text: str, translated_metrics: Mapping[str, TranslatedMetric]) -> str:
    """Replace expressions in strings like CPU Load - %(load1:max@count) CPU Cores"""
    # Note: The 'CPU load' graph is the only example with such a replacement. We do not want to
    # offer such replacements in a generic way.
    reg = regex.regex(r"%\([^)]*\)")
    if m := reg.search(text):
        if (
            result := parse_legacy_simple_expression(m.group()[2:-1], translated_metrics).evaluate(
                translated_metrics
            )
        ).is_error():
            return text.split("-")[0].strip()
        return reg.sub(
            get_render_function(result.ok.unit_spec)(result.ok.value).strip(),
            text,
        )

    return text


def _horizontal_rules_from_thresholds(
    metric_expressions: Iterable[MetricExpression],
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Sequence[HorizontalRule]:
    horizontal_rules = []
    for metric_expression in metric_expressions:
        if (result := metric_expression.evaluate(translated_metrics)).is_error():
            # Scalar value like min and max are always optional. This makes configuration
            # of graphs easier.
            if result.error.metric_name:
                continue
            return []

        horizontal_rules.append(
            HorizontalRule(
                value=result.ok.value,
                rendered_value=get_render_function(result.ok.unit_spec)(result.ok.value),
                color=result.ok.color,
                title=metric_expression.title,
            )
        )
    return horizontal_rules


def create_graph_recipe_from_template(
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    graph_template: GraphTemplate,
    translated_metrics: Mapping[str, TranslatedMetric],
    specification: GraphSpecification,
) -> GraphRecipe:
    def _graph_metric(metric_expression: MetricExpression) -> GraphMetric:
        unit_color = compute_unit_color(
            metric_expression,
            translated_metrics,
            graph_template.optional_metrics,
        )
        return GraphMetric(
            title=compute_title(metric_expression, translated_metrics),
            line_type=metric_expression.line_type,
            operation=metric_expression_to_graph_recipe_expression(
                site_id,
                host_name,
                service_name,
                metric_expression,
                translated_metrics,
                graph_template.consolidation_function or "max",
            ),
            unit=unit_color.unit if unit_color else "",
            color=unit_color.color if unit_color else "#000000",
        )

    metrics = list(map(_graph_metric, graph_template.metrics))
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

    title = _replace_expressions(graph_template.title or "", translated_metrics)
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
        horizontal_rules=_horizontal_rules_from_thresholds(
            graph_template.scalars, translated_metrics
        ),  # e.g. lines for WARN and CRIT
        omit_zero_metrics=graph_template.omit_zero_metrics,
        consolidation_function=graph_template.consolidation_function or "max",
        specification=specification,
    )


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


def _evaluate_graph_template_range_boundary(
    metric_expression: BaseMetricExpression, translated_metrics: Mapping[str, TranslatedMetric]
) -> float | None:
    if (result := metric_expression.evaluate(translated_metrics)).is_error():
        return None
    return result.ok.value


def _to_metric_operation(
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    metric_expression: BaseMetricExpression,
    translated_metrics: Mapping[str, TranslatedMetric],
    consolidation_function: GraphConsolidationFunction | None,
) -> MetricOpRRDSource | MetricOpOperator | MetricOpConstant:
    match metric_expression:
        case Constant():
            return MetricOpConstant(value=float(metric_expression.value))
        case Metric():
            metrics = [
                MetricOpRRDSource(
                    site_id=site_id,
                    host_name=host_name,
                    service_name=service_name,
                    metric_name=pnp_cleanup(o.name),
                    consolidation_func_name=(
                        metric_expression.consolidation or consolidation_function
                    ),
                    scale=o.scale,
                )
                for o in translated_metrics[metric_expression.name].originals
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
                    for s in metric_expression.summands
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
                    for f in metric_expression.factors
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
                        metric_expression.minuend,
                        translated_metrics,
                        consolidation_function,
                    ),
                    _to_metric_operation(
                        site_id,
                        host_name,
                        service_name,
                        metric_expression.subtrahend,
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
                        metric_expression.dividend,
                        translated_metrics,
                        consolidation_function,
                    ),
                    _to_metric_operation(
                        site_id,
                        host_name,
                        service_name,
                        metric_expression.divisor,
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
                    for o in metric_expression.operands
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
                    for o in metric_expression.operands
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
                    for o in metric_expression.operands
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
                    for o in metric_expression.operands
                ],
            )
        case _:
            raise TypeError(metric_expression)


def metric_expression_to_graph_recipe_expression(
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    metric_expression: MetricExpression,
    translated_metrics: Mapping[str, TranslatedMetric],
    consolidation_function: GraphConsolidationFunction | None,
) -> MetricOpRRDSource | MetricOpOperator | MetricOpConstant:
    return _to_metric_operation(
        site_id,
        host_name,
        service_name,
        metric_expression.base,
        translated_metrics,
        consolidation_function,
    )

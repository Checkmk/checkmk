#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never, ClassVar, Literal

from livestatus import SiteId

from cmk.utils import pnp_cleanup, regex
from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.gui.i18n import _, translate_to_current_language
from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import Row
from cmk.gui.utils.speaklater import LazyString

from cmk.ccc.exceptions import MKGeneralException
from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api

from ._color import parse_color_from_api
from ._expression import (
    Average,
    BaseMetricExpression,
    Constant,
    CriticalOf,
    Difference,
    Fraction,
    Maximum,
    MaximumOf,
    Merge,
    Metric,
    MetricExpression,
    Minimum,
    MinimumOf,
    parse_base_expression,
    parse_expression,
    Product,
    Sum,
    WarningOf,
)
from ._from_api import graphs_from_api, register_unit_info
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
from ._legacy import graph_info, RawGraphTemplate
from ._metrics import get_metric_spec
from ._translated_metrics import translated_metrics_from_row, TranslatedMetric
from ._type_defs import GraphConsolidationFunction, LineType
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
    unit: str
    color: str


@dataclass(frozen=True)
class MetricDefinition:
    expression: MetricExpression


def compute_title(
    expression: MetricExpression, translated_metrics: Mapping[str, TranslatedMetric]
) -> str:
    if expression.title:
        return expression.title
    return translated_metrics[next(expression.metric_names())].title


def compute_unit_color(
    expression: MetricExpression,
    translated_metrics: Mapping[str, TranslatedMetric],
    optional_metrics: Sequence[str],
) -> MetricUnitColor | None:
    try:
        result = expression.evaluate(translated_metrics)
    except KeyError as err:  # because metric_name is not in translated_metrics
        metric_name = err.args[0]
        if optional_metrics and metric_name in optional_metrics:
            return None
        raise MKGeneralException(
            _("Graph recipe '%s' uses undefined metric '%s', available are: %s")
            % (
                expression,
                metric_name,
                ", ".join(sorted(translated_metrics.keys())) or "None",
            )
        )
    return MetricUnitColor(result.unit_info.id, result.color)


def _parse_quantity(
    quantity: (
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
    ),
    line_type: Literal["line", "-line", "stack", "-stack"],
) -> MetricDefinition:
    match quantity:
        case str():
            return MetricDefinition(
                expression=MetricExpression(
                    Metric(quantity),
                    line_type=line_type,
                    title=get_metric_spec(quantity).title,
                ),
            )
        case metrics_api.Constant():
            return MetricDefinition(
                expression=MetricExpression(
                    Constant(quantity.value),
                    line_type=line_type,
                    title=str(quantity.title.localize(translate_to_current_language)),
                    unit_id=register_unit_info(quantity.unit).id,
                    color=parse_color_from_api(quantity.color),
                ),
            )
        case metrics_api.WarningOf():
            return MetricDefinition(
                expression=MetricExpression(
                    WarningOf(Metric(quantity.metric_name)),
                    line_type=line_type,
                    title=_("Warning of %s") % get_metric_spec(quantity.metric_name).title,
                ),
            )
        case metrics_api.CriticalOf():
            return MetricDefinition(
                expression=MetricExpression(
                    CriticalOf(Metric(quantity.metric_name)),
                    line_type=line_type,
                    title=_("Critical of %s") % get_metric_spec(quantity.metric_name).title,
                ),
            )
        case metrics_api.MinimumOf():
            return MetricDefinition(
                expression=MetricExpression(
                    MinimumOf(Metric(quantity.metric_name)),
                    line_type=line_type,
                    title=get_metric_spec(quantity.metric_name).title,
                    color=parse_color_from_api(quantity.color),
                ),
            )
        case metrics_api.MaximumOf():
            return MetricDefinition(
                expression=MetricExpression(
                    MaximumOf(Metric(quantity.metric_name)),
                    line_type=line_type,
                    title=get_metric_spec(quantity.metric_name).title,
                    color=parse_color_from_api(quantity.color),
                ),
            )
        case metrics_api.Sum():
            return MetricDefinition(
                expression=MetricExpression(
                    Sum([_parse_quantity(s, line_type).expression.base for s in quantity.summands]),
                    line_type=line_type,
                    title=str(quantity.title.localize(translate_to_current_language)),
                    color=parse_color_from_api(quantity.color),
                ),
            )
        case metrics_api.Product():
            return MetricDefinition(
                expression=MetricExpression(
                    Product(
                        [_parse_quantity(f, line_type).expression.base for f in quantity.factors]
                    ),
                    line_type=line_type,
                    title=str(quantity.title.localize(translate_to_current_language)),
                    unit_id=register_unit_info(quantity.unit).id,
                    color=parse_color_from_api(quantity.color),
                ),
            )
        case metrics_api.Difference():
            return MetricDefinition(
                expression=MetricExpression(
                    Difference(
                        minuend=_parse_quantity(quantity.minuend, line_type).expression.base,
                        subtrahend=_parse_quantity(quantity.subtrahend, line_type).expression.base,
                    ),
                    line_type=line_type,
                    title=str(quantity.title.localize(translate_to_current_language)),
                    color=parse_color_from_api(quantity.color),
                ),
            )
        case metrics_api.Fraction():
            return MetricDefinition(
                expression=MetricExpression(
                    Fraction(
                        dividend=_parse_quantity(quantity.dividend, line_type).expression.base,
                        divisor=_parse_quantity(quantity.divisor, line_type).expression.base,
                    ),
                    line_type=line_type,
                    title=str(quantity.title.localize(translate_to_current_language)),
                    unit_id=register_unit_info(quantity.unit).id,
                    color=parse_color_from_api(quantity.color),
                ),
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
            else _parse_quantity(minimal_range.lower, "line").expression.base
        ),
        max=(
            Constant(minimal_range.upper)
            if isinstance(minimal_range.upper, (int, float))
            else _parse_quantity(minimal_range.upper, "line").expression.base
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
    metrics: Sequence[MetricDefinition]


def _graph_template_from_api_graph(id_: str, graph: graphs_api.Graph) -> GraphTemplate:
    metrics = [_parse_quantity(l, "stack") for l in graph.compound_lines]
    scalars: list[MetricExpression] = []
    for line in graph.simple_lines:
        match line:
            case (
                metrics_api.WarningOf()
                | metrics_api.CriticalOf()
                | metrics_api.MinimumOf()
                | metrics_api.MaximumOf()
            ):
                scalars.append(_parse_quantity(line, "line").expression)
            case _:
                metrics.append(_parse_quantity(line, "line"))
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

    metrics = [_parse_quantity(l, "-stack") for l in bidirectional.lower.compound_lines] + [
        _parse_quantity(l, "stack") for l in bidirectional.upper.compound_lines
    ]
    scalars: list[MetricExpression] = []
    for line in bidirectional.lower.simple_lines:
        match line:
            case (
                metrics_api.WarningOf()
                | metrics_api.CriticalOf()
                | metrics_api.MinimumOf()
                | metrics_api.MaximumOf()
            ):
                scalars.append(_parse_quantity(line, "-line").expression)
            case _:
                metrics.append(_parse_quantity(line, "-line"))
    for line in bidirectional.upper.simple_lines:
        match line:
            case (
                metrics_api.WarningOf()
                | metrics_api.CriticalOf()
                | metrics_api.MinimumOf()
                | metrics_api.MaximumOf()
            ):
                scalars.append(_parse_quantity(line, "line").expression)
            case _:
                metrics.append(_parse_quantity(line, "line"))
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
    raw_scalar_expression: str | tuple[str, str | LazyString]
) -> MetricExpression:
    if isinstance(raw_scalar_expression, tuple):
        return parse_expression(raw_scalar_expression[0], "line", str(raw_scalar_expression[1]), {})

    if raw_scalar_expression.endswith(":warn"):
        title = _("Warning")
    elif raw_scalar_expression.endswith(":crit"):
        title = _("Critical")
    else:
        title = raw_scalar_expression
    return parse_expression(raw_scalar_expression, "line", str(title), {})


def _parse_raw_graph_range(raw_graph_range: tuple[int | str, int | str]) -> FixedGraphTemplateRange:
    return FixedGraphTemplateRange(
        min=parse_base_expression(raw_graph_range[0], {}),
        max=parse_base_expression(raw_graph_range[1], {}),
    )


def _parse_raw_metric_definition(
    raw_metric_definition: (
        tuple[str, LineType] | tuple[str, LineType, str] | tuple[str, LineType, LazyString]
    )
) -> MetricDefinition:
    raw_expression, line_type, *title = raw_metric_definition
    return MetricDefinition(
        parse_expression(raw_expression, line_type, str(title[0]) if title else "", {}),
    )


def _graph_template_from_legacy(id_: str, raw: RawGraphTemplate) -> GraphTemplate:
    return GraphTemplate(
        id=id_,
        title=_parse_title(raw),
        scalars=[_parse_raw_scalar_expression(r) for r in raw.get("scalars", [])],
        conflicting_metrics=raw.get("conflicting_metrics", []),
        optional_metrics=raw.get("optional_metrics", []),
        consolidation_function=raw.get("consolidation_function"),
        range=(_parse_raw_graph_range(raw_range) if (raw_range := raw.get("range")) else None),
        omit_zero_metrics=raw.get("omit_zero_metrics", False),
        metrics=[_parse_raw_metric_definition(r) for r in raw["metrics"]],
    )


def _parse_graph_template(
    id_: str, template: graphs_api.Graph | graphs_api.Bidirectional | RawGraphTemplate
) -> GraphTemplate:
    match template:
        case graphs_api.Graph():
            return _graph_template_from_api_graph(id_, template)
        case graphs_api.Bidirectional():
            return _graph_template_from_api_bidirectional(id_, template)
        case _:
            return _graph_template_from_legacy(id_, template)


def graph_template_from_name(name: str) -> GraphTemplate:
    if name.startswith("METRIC_"):
        name = name[7:]
    return GraphTemplate(
        id=f"METRIC_{name}",
        title="",
        metrics=[MetricDefinition(expression=MetricExpression(Metric(name), line_type="area"))],
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
    translated_metrics: Mapping[str, TranslatedMetric], metrics: Sequence[MetricDefinition]
) -> Iterator[MetricDefinition]:
    for metric_defintion in metrics:
        line_type: Literal["line", "-line"] = (
            "-line" if metric_defintion.expression.line_type.startswith("-") else "line"
        )
        for metric_name in metric_defintion.expression.metric_names():
            if (predict_metric_name := f"predict_{metric_name}") in translated_metrics:
                yield MetricDefinition(
                    MetricExpression(Metric(predict_metric_name), line_type=line_type)
                )
            if (predict_lower_metric_name := f"predict_lower_{metric_name}") in translated_metrics:
                yield MetricDefinition(
                    MetricExpression(Metric(predict_lower_metric_name), line_type=line_type),
                )


def _filter_renderable_graph_metrics(
    metric_definitions: Sequence[MetricDefinition],
    translated_metrics: Mapping[str, TranslatedMetric],
    optional_metrics: Sequence[str],
) -> Iterator[MetricDefinition]:
    for metric_definition in metric_definitions:
        try:
            metric_definition.expression.evaluate(translated_metrics)
            yield metric_definition
        except KeyError as err:  # because can't find necessary metric_name in translated_metrics
            metric_name = err.args[0]
            if metric_name in optional_metrics:
                continue
            raise err


def _applicable_metrics(
    *,
    metrics_to_consider: Sequence[MetricDefinition],
    conflicting_metrics: Iterable[str],
    optional_metrics: Sequence[str],
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Sequence[MetricDefinition]:
    # Skip early on conflicting_metrics
    for var in conflicting_metrics:
        if var in translated_metrics:
            return []

    try:
        return list(
            _filter_renderable_graph_metrics(
                metrics_to_consider,
                translated_metrics,
                optional_metrics,
            )
        )
    except KeyError:
        return []


def get_graph_templates(
    translated_metrics: Mapping[str, TranslatedMetric]
) -> Iterator[GraphTemplate]:
    if not translated_metrics:
        yield from ()
        return

    explicit_templates = [
        GraphTemplate(
            id=parsed.id,
            title=parsed.title,
            scalars=parsed.scalars,
            conflicting_metrics=parsed.conflicting_metrics,
            optional_metrics=parsed.optional_metrics,
            consolidation_function=parsed.consolidation_function,
            range=parsed.range,
            omit_zero_metrics=parsed.omit_zero_metrics,
            metrics=(
                list(metrics) + list(_compute_predictive_metrics(translated_metrics, metrics))
            ),
        )
        for id_, template in _graph_templates_from_plugins()
        for parsed in (_parse_graph_template(id_, template),)
        if (
            metrics := _applicable_metrics(
                metrics_to_consider=parsed.metrics,
                conflicting_metrics=parsed.conflicting_metrics,
                optional_metrics=parsed.optional_metrics,
                translated_metrics=translated_metrics,
            )
        )
    ]
    yield from explicit_templates

    already_graphed_metrics = {
        n for gt in explicit_templates for md in gt.metrics for n in md.expression.metric_names()
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
        try:
            result = parse_base_expression(m.group()[2:-1], translated_metrics).evaluate(
                translated_metrics
            )
        except (ValueError, KeyError):
            return text.split("-")[0].strip()
        return reg.sub(result.unit_info.render(result.value).strip(), text)

    return text


def _horizontal_rules_from_thresholds(
    thresholds: Iterable[MetricExpression],
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Sequence[HorizontalRule]:
    horizontal_rules = []
    for expression in thresholds:
        try:
            if (result := expression.evaluate(translated_metrics)).value:
                horizontal_rules.append(
                    HorizontalRule(
                        value=result.value,
                        rendered_value=result.unit_info.render(result.value),
                        color=result.color,
                        title=expression.title,
                    )
                )
        # Scalar value like min and max are always optional. This makes configuration
        # of graphs easier.
        except Exception:
            pass

    return horizontal_rules


def create_graph_recipe_from_template(
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    graph_template: GraphTemplate,
    translated_metrics: Mapping[str, TranslatedMetric],
    specification: GraphSpecification,
) -> GraphRecipe:
    def _graph_metric(metric_definition: MetricDefinition) -> GraphMetric:
        unit_color = compute_unit_color(
            metric_definition.expression,
            translated_metrics,
            graph_template.optional_metrics,
        )
        return GraphMetric(
            title=compute_title(metric_definition.expression, translated_metrics),
            line_type=metric_definition.expression.line_type,
            operation=metric_expression_to_graph_recipe_expression(
                site_id,
                host_name,
                service_name,
                metric_definition.expression,
                translated_metrics,
                graph_template.consolidation_function or "max",
            ),
            unit=unit_color.unit if unit_color else "",
            color=unit_color.color if unit_color else "#000000",
        )

    metrics = list(map(_graph_metric, graph_template.metrics))
    units = {m.unit for m in metrics}
    if len(units) > 1:
        raise MKGeneralException(
            _("Cannot create graph with metrics of different units '%s'") % ", ".join(units)
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
        unit=units.pop(),
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
    boundary: BaseMetricExpression, translated_metrics: Mapping[str, TranslatedMetric]
) -> float | None:
    try:
        return boundary.evaluate(translated_metrics).value
    except Exception:
        return None


def _to_metric_operation(
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    expression: BaseMetricExpression,
    translated_metrics: Mapping[str, TranslatedMetric],
    enforced_consolidation_function: GraphConsolidationFunction | None,
) -> MetricOpRRDSource | MetricOpOperator | MetricOpConstant:
    match expression:
        case Constant():
            return MetricOpConstant(value=float(expression.value))
        case Metric():
            metrics = [
                MetricOpRRDSource(
                    site_id=site_id,
                    host_name=host_name,
                    service_name=service_name,
                    metric_name=pnp_cleanup(original.name),
                    consolidation_func_name=(
                        expression.consolidation or enforced_consolidation_function
                    ),
                    scale=original.scale,
                )
                for original in translated_metrics[expression.name].originals
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
                        enforced_consolidation_function,
                    )
                    for s in expression.summands
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
                        enforced_consolidation_function,
                    )
                    for f in expression.factors
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
                        expression.minuend,
                        translated_metrics,
                        enforced_consolidation_function,
                    ),
                    _to_metric_operation(
                        site_id,
                        host_name,
                        service_name,
                        expression.subtrahend,
                        translated_metrics,
                        enforced_consolidation_function,
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
                        expression.dividend,
                        translated_metrics,
                        enforced_consolidation_function,
                    ),
                    _to_metric_operation(
                        site_id,
                        host_name,
                        service_name,
                        expression.divisor,
                        translated_metrics,
                        enforced_consolidation_function,
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
                        enforced_consolidation_function,
                    )
                    for o in expression.operands
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
                        enforced_consolidation_function,
                    )
                    for o in expression.operands
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
                        enforced_consolidation_function,
                    )
                    for o in expression.operands
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
                        enforced_consolidation_function,
                    )
                    for o in expression.operands
                ],
            )
        case _:
            raise TypeError(expression)


def metric_expression_to_graph_recipe_expression(
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    metric_expression: MetricExpression,
    translated_metrics: Mapping[str, TranslatedMetric],
    enforced_consolidation_function: GraphConsolidationFunction | None,
) -> MetricOpRRDSource | MetricOpOperator | MetricOpConstant:
    return _to_metric_operation(
        site_id,
        host_name,
        service_name,
        metric_expression.base,
        translated_metrics,
        enforced_consolidation_function,
    )


def find_matching_rows_and_translated_metrics(
    rows: Sequence[Row],
    metric_definitions: Sequence[MetricDefinition],
    *,
    conflicting_metrics: Sequence[str],
    optional_metrics: Sequence[str],
) -> Iterator[tuple[Row, Mapping[str, TranslatedMetric]]]:
    for row in rows:
        translated_metrics = translated_metrics_from_row(row)
        if _applicable_metrics(
            metrics_to_consider=metric_definitions,
            conflicting_metrics=conflicting_metrics,
            optional_metrics=optional_metrics,
            translated_metrics=translated_metrics,
        ):
            yield row, translated_metrics

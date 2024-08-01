#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Container, Iterable, Literal, Self

from cmk.gui.i18n import _, translate_to_current_language
from cmk.gui.utils.speaklater import LazyString

from cmk.ccc.exceptions import MKGeneralException
from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api

from ._color import parse_color_from_api
from ._expression import (
    Constant,
    CriticalOf,
    Difference,
    Fraction,
    Maximum,
    MaximumOf,
    Metric,
    MetricExpression,
    Minimum,
    MinimumOf,
    parse_expression,
    Product,
    Sum,
    WarningOf,
)
from ._legacy import graph_info, RawGraphTemplate
from ._loader import graphs_from_api, register_unit
from ._type_defs import GraphConsoldiationFunction, LineType, TranslatedMetric
from ._utils import get_extended_metric_info


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
class ScalarDefinition:
    expression: MetricExpression
    title: str


@dataclass(frozen=True)
class MetricUnitColor:
    unit: str
    color: str


@dataclass(frozen=True)
class MetricDefinition:
    expression: MetricExpression
    line_type: LineType
    title: str = ""

    def compute_title(self, translated_metrics: Mapping[str, TranslatedMetric]) -> str:
        if self.title:
            return self.title
        return translated_metrics[next(self.expression.metrics()).name].title

    def compute_unit_color(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
        optional_metrics: Sequence[str],
    ) -> MetricUnitColor | None:
        try:
            result = self.expression.evaluate(translated_metrics)
        except KeyError as err:  # because metric_name is not in translated_metrics
            metric_name = err.args[0]
            if optional_metrics and metric_name in optional_metrics:
                return None
            raise MKGeneralException(
                _("Graph recipe '%s' uses undefined metric '%s', available are: %s")
                % (
                    self.expression,
                    metric_name,
                    ", ".join(sorted(translated_metrics.keys())) or "None",
                )
            )
        return MetricUnitColor(result.unit_info.id, result.color)


def _parse_raw_metric_definition(
    raw_metric_definition: (
        tuple[str, LineType] | tuple[str, LineType, str] | tuple[str, LineType, LazyString]
    )
) -> MetricDefinition:
    expression, line_type, *title = raw_metric_definition
    return MetricDefinition(
        expression=parse_expression(expression, {}),
        line_type=line_type,
        title=str(title[0]) if title else "",
    )


def _parse_raw_scalar_definition(
    raw_scalar_definition: str | tuple[str, str | LazyString]
) -> ScalarDefinition:
    if isinstance(raw_scalar_definition, tuple):
        return ScalarDefinition(
            expression=parse_expression(raw_scalar_definition[0], {}),
            title=str(raw_scalar_definition[1]),
        )

    if raw_scalar_definition.endswith(":warn"):
        title = _("Warning")
    elif raw_scalar_definition.endswith(":crit"):
        title = _("Critical")
    else:
        title = raw_scalar_definition
    return ScalarDefinition(
        expression=parse_expression(raw_scalar_definition, {}),
        title=str(title),
    )


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
                expression=Metric(quantity),
                line_type=line_type,
                title=str(get_extended_metric_info(quantity).title),
            )
        case metrics_api.Constant():
            return MetricDefinition(
                expression=Constant(
                    quantity.value,
                    explicit_unit_id=register_unit(quantity.unit).id,
                    explicit_color=parse_color_from_api(quantity.color),
                ),
                line_type=line_type,
                title=str(quantity.title.localize(translate_to_current_language)),
            )
        case metrics_api.WarningOf():
            metric_ = get_extended_metric_info(quantity.metric_name)
            return MetricDefinition(
                expression=WarningOf(Metric(quantity.metric_name)),
                line_type=line_type,
                title=_("Warning of %s") % metric_.title,
            )
        case metrics_api.CriticalOf():
            metric_ = get_extended_metric_info(quantity.metric_name)
            return MetricDefinition(
                expression=CriticalOf(Metric(quantity.metric_name)),
                line_type=line_type,
                title=_("Critical of %s") % metric_.title,
            )
        case metrics_api.MinimumOf():
            metric_ = get_extended_metric_info(quantity.metric_name)
            return MetricDefinition(
                expression=MinimumOf(
                    Metric(quantity.metric_name),
                    explicit_color=parse_color_from_api(quantity.color),
                ),
                line_type=line_type,
                title=str(metric_.title),
            )
        case metrics_api.MaximumOf():
            metric_ = get_extended_metric_info(quantity.metric_name)
            return MetricDefinition(
                expression=MaximumOf(
                    Metric(quantity.metric_name),
                    explicit_color=parse_color_from_api(quantity.color),
                ),
                line_type=line_type,
                title=str(metric_.title),
            )
        case metrics_api.Sum():
            return MetricDefinition(
                expression=Sum(
                    [_parse_quantity(s, line_type).expression for s in quantity.summands],
                    explicit_color=parse_color_from_api(quantity.color),
                ),
                line_type=line_type,
                title=str(quantity.title.localize(translate_to_current_language)),
            )
        case metrics_api.Product():
            return MetricDefinition(
                expression=Product(
                    [_parse_quantity(f, line_type).expression for f in quantity.factors],
                    explicit_unit_id=register_unit(quantity.unit).id,
                    explicit_color=parse_color_from_api(quantity.color),
                ),
                line_type=line_type,
                title=str(quantity.title.localize(translate_to_current_language)),
            )
        case metrics_api.Difference():
            return MetricDefinition(
                expression=Difference(
                    minuend=_parse_quantity(quantity.minuend, line_type).expression,
                    subtrahend=_parse_quantity(quantity.subtrahend, line_type).expression,
                    explicit_color=parse_color_from_api(quantity.color),
                ),
                line_type=line_type,
                title=str(quantity.title.localize(translate_to_current_language)),
            )
        case metrics_api.Fraction():
            return MetricDefinition(
                expression=Fraction(
                    dividend=_parse_quantity(quantity.dividend, line_type).expression,
                    divisor=_parse_quantity(quantity.divisor, line_type).expression,
                    explicit_unit_id=register_unit(quantity.unit).id,
                    explicit_color=parse_color_from_api(quantity.color),
                ),
                line_type=line_type,
                title=str(quantity.title.localize(translate_to_current_language)),
            )


@dataclass(frozen=True, kw_only=True)
class FixedGraphTemplateRange:
    min: MetricExpression
    max: MetricExpression


@dataclass(frozen=True, kw_only=True)
class MinimalGraphTemplateRange:
    min: MetricExpression
    max: MetricExpression


def _parse_raw_graph_range(raw_graph_range: tuple[int | str, int | str]) -> FixedGraphTemplateRange:
    return FixedGraphTemplateRange(
        min=parse_expression(raw_graph_range[0], {}),
        max=parse_expression(raw_graph_range[1], {}),
    )


def _parse_minimal_range(
    minimal_range: graphs_api.MinimalRange,
) -> MinimalGraphTemplateRange:
    return MinimalGraphTemplateRange(
        min=(
            Constant(minimal_range.lower)
            if isinstance(minimal_range.lower, (int, float))
            else _parse_quantity(minimal_range.lower, "line").expression
        ),
        max=(
            Constant(minimal_range.upper)
            if isinstance(minimal_range.upper, (int, float))
            else _parse_quantity(minimal_range.upper, "line").expression
        ),
    )


@dataclass(frozen=True)
class GraphTemplate:
    id: str
    title: str
    scalars: Sequence[ScalarDefinition]
    conflicting_metrics: Sequence[str]
    optional_metrics: Sequence[str]
    consolidation_function: GraphConsoldiationFunction | None
    range: FixedGraphTemplateRange | MinimalGraphTemplateRange | None
    omit_zero_metrics: bool
    metrics: Sequence[MetricDefinition]

    @classmethod
    def from_name(cls, name: str) -> Self:
        if name.startswith("METRIC_"):
            name = name[7:]
        return cls(
            id=f"METRIC_{name}",
            title="",
            metrics=[MetricDefinition(expression=Metric(name), line_type="area")],
            scalars=[
                ScalarDefinition(expression=WarningOf(Metric(name)), title=str(_("Warning"))),
                ScalarDefinition(expression=CriticalOf(Metric(name)), title=str(_("Critical"))),
            ],
            conflicting_metrics=[],
            optional_metrics=[],
            consolidation_function=None,
            range=None,
            omit_zero_metrics=False,
        )

    @classmethod
    def from_raw(cls, id_: str, raw: RawGraphTemplate) -> Self:
        return cls(
            id=id_,
            title=_parse_title(raw),
            scalars=[_parse_raw_scalar_definition(r) for r in raw.get("scalars", [])],
            conflicting_metrics=raw.get("conflicting_metrics", []),
            optional_metrics=raw.get("optional_metrics", []),
            consolidation_function=raw.get("consolidation_function"),
            range=(_parse_raw_graph_range(raw_range) if (raw_range := raw.get("range")) else None),
            omit_zero_metrics=raw.get("omit_zero_metrics", False),
            metrics=[_parse_raw_metric_definition(r) for r in raw["metrics"]],
        )

    @classmethod
    def from_graph(cls, id_: str, graph: graphs_api.Graph) -> Self:
        metrics_ = [_parse_quantity(l, "stack") for l in graph.compound_lines]
        scalars: list[ScalarDefinition] = []
        for line in graph.simple_lines:
            match line:
                case (
                    metrics_api.WarningOf()
                    | metrics_api.CriticalOf()
                    | metrics_api.MinimumOf()
                    | metrics_api.MaximumOf()
                ):
                    parsed = _parse_quantity(line, "line")
                    scalars.append(ScalarDefinition(parsed.expression, parsed.title))
                case _:
                    metrics_.append(_parse_quantity(line, "line"))
        return cls(
            id=id_,
            title=_parse_title(graph),
            range=(
                None if graph.minimal_range is None else _parse_minimal_range(graph.minimal_range)
            ),
            metrics=metrics_,
            scalars=list(scalars),
            optional_metrics=graph.optional,
            conflicting_metrics=graph.conflicting,
            consolidation_function=None,
            omit_zero_metrics=False,
        )

    @classmethod
    def from_bidirectional(cls, id_: str, bidirectional: graphs_api.Bidirectional) -> Self:
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

        metrics_ = [_parse_quantity(l, "-stack") for l in bidirectional.lower.compound_lines] + [
            _parse_quantity(l, "stack") for l in bidirectional.upper.compound_lines
        ]
        scalars: list[ScalarDefinition] = []
        for line in bidirectional.lower.simple_lines:
            match line:
                case (
                    metrics_api.WarningOf()
                    | metrics_api.CriticalOf()
                    | metrics_api.MinimumOf()
                    | metrics_api.MaximumOf()
                ):
                    parsed = _parse_quantity(line, "-line")
                    scalars.append(ScalarDefinition(parsed.expression, parsed.title))
                case _:
                    metrics_.append(_parse_quantity(line, "-line"))
        for line in bidirectional.upper.simple_lines:
            match line:
                case (
                    metrics_api.WarningOf()
                    | metrics_api.CriticalOf()
                    | metrics_api.MinimumOf()
                    | metrics_api.MaximumOf()
                ):
                    parsed = _parse_quantity(line, "line")
                    scalars.append(ScalarDefinition(parsed.expression, parsed.title))
                case _:
                    metrics_.append(_parse_quantity(line, "line"))
        return cls(
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
            metrics=metrics_,
            scalars=scalars,
            optional_metrics=(
                list(bidirectional.lower.optional) + list(bidirectional.upper.optional)
            ),
            conflicting_metrics=(
                list(bidirectional.lower.conflicting) + list(bidirectional.upper.conflicting)
            ),
            consolidation_function=None,
            omit_zero_metrics=False,
        )


def _parse_graph_template(
    id_: str, template: graphs_api.Graph | graphs_api.Bidirectional | RawGraphTemplate
) -> GraphTemplate:
    match template:
        case graphs_api.Graph():
            return GraphTemplate.from_graph(id_, template)
        case graphs_api.Bidirectional():
            return GraphTemplate.from_bidirectional(id_, template)
        case _:
            return GraphTemplate.from_raw(id_, template)


def get_graph_template(template_id: str) -> GraphTemplate:
    if template_id.startswith("METRIC_"):
        return GraphTemplate.from_name(template_id)
    for id_, template in _graph_templates_from_plugins():
        if template_id == id_:
            return _parse_graph_template(id_, template)
    raise MKGeneralException(_("There is no graph template with the id '%s'") % template_id)


def _compute_predictive_metrics(
    translated_metrics: Mapping[str, TranslatedMetric], metrics_: Sequence[MetricDefinition]
) -> Iterator[MetricDefinition]:
    for metric_defintion in metrics_:
        line_type: Literal["line", "-line"] = (
            "-line" if metric_defintion.line_type.startswith("-") else "line"
        )
        for metric in metric_defintion.expression.metrics():
            if (predict_metric_name := f"predict_{metric.name}") in translated_metrics:
                yield MetricDefinition(
                    expression=Metric(predict_metric_name),
                    line_type=line_type,
                )
            if (predict_lower_metric_name := f"predict_lower_{metric.name}") in translated_metrics:
                yield MetricDefinition(
                    expression=Metric(predict_lower_metric_name),
                    line_type=line_type,
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


def applicable_metrics(
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


def _get_explicit_graph_templates(
    graph_templates: Iterable[
        tuple[str, graphs_api.Graph | graphs_api.Bidirectional | RawGraphTemplate]
    ],
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Iterable[GraphTemplate]:
    for id_, template in graph_templates:
        parsed = _parse_graph_template(id_, template)
        if metrics_ := applicable_metrics(
            metrics_to_consider=parsed.metrics,
            conflicting_metrics=parsed.conflicting_metrics,
            optional_metrics=parsed.optional_metrics,
            translated_metrics=translated_metrics,
        ):
            yield GraphTemplate(
                id=parsed.id,
                title=parsed.title,
                scalars=parsed.scalars,
                conflicting_metrics=parsed.conflicting_metrics,
                optional_metrics=parsed.optional_metrics,
                consolidation_function=parsed.consolidation_function,
                range=parsed.range,
                omit_zero_metrics=parsed.omit_zero_metrics,
                metrics=(
                    list(metrics_) + list(_compute_predictive_metrics(translated_metrics, metrics_))
                ),
            )


def _get_implicit_graph_templates(
    translated_metrics: Mapping[str, TranslatedMetric],
    already_graphed_metrics: Container[str],
) -> Iterable[GraphTemplate]:
    for metric_name, translated_metric in sorted(translated_metrics.items()):
        if translated_metric.auto_graph and metric_name not in already_graphed_metrics:
            yield GraphTemplate.from_name(metric_name)


def get_graph_templates(
    translated_metrics: Mapping[str, TranslatedMetric]
) -> Iterator[GraphTemplate]:
    if not translated_metrics:
        yield from ()
        return

    explicit_templates = list(
        _get_explicit_graph_templates(
            _graph_templates_from_plugins(),
            translated_metrics,
        )
    )
    yield from explicit_templates
    yield from _get_implicit_graph_templates(
        translated_metrics,
        {m.name for gt in explicit_templates for md in gt.metrics for m in md.expression.metrics()},
    )

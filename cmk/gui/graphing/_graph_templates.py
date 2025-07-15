#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import itertools
import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never, Literal

from pydantic import BaseModel

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

from cmk.utils.servicename import ServiceName

from cmk.gui.config import active_config
from cmk.gui.graphing._unit import user_specific_unit
from cmk.gui.i18n import _, translate_to_current_language
from cmk.gui.logged_in import user
from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import Row, VisualContext
from cmk.gui.visuals import livestatus_query_bare

from cmk.graphing.v1 import graphs as graphs_api

from ._from_api import RegisteredMetric
from ._graph_specification import (
    compute_warn_crit_rules_from_translated_metric,
    FixedVerticalRange,
    graph_specification_registry,
    GraphMetric,
    GraphRecipe,
    GraphSpecification,
    HorizontalRule,
    MinimalVerticalRange,
)
from ._graphs_order import GRAPHS_ORDER
from ._metric_expression import (
    BaseMetricExpression,
    Constant,
    CriticalOf,
    Evaluated,
    Maximum,
    MaximumOf,
    Metric,
    MetricExpression,
    Minimum,
    MinimumOf,
    parse_base_expression_from_api,
    parse_expression_from_api,
    WarningOf,
)
from ._metric_operation import (
    AnnotatedHostName,
    GraphConsolidationFunction,
)
from ._translated_metrics import translated_metrics_from_row, TranslatedMetric
from ._unit import ConvertibleUnitSpecification
from ._utils import get_graph_data_from_livestatus


class MKGraphNotFound(MKGeneralException): ...


def _sort_registered_graph_plugins(
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
) -> list[tuple[str, graphs_api.Graph | graphs_api.Bidirectional]]:
    def _by_index(graph_name: str) -> int:
        try:
            return GRAPHS_ORDER.index(graph_name)
        except ValueError:
            return -1

    return sorted(registered_graphs.items(), key=lambda t: _by_index(t[0]))


def _parse_title(template: graphs_api.Graph | graphs_api.Bidirectional) -> str:
    return template.title.localize(translate_to_current_language)


@dataclass(frozen=True)
class GraphTemplateChoice:
    id: str
    title: str


def get_graph_template_choices(
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
) -> list[GraphTemplateChoice]:
    return sorted(
        [
            GraphTemplateChoice(graph.name, _parse_title(graph))
            for graph in registered_graphs.values()
        ],
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
            if isinstance(minimal_range.lower, int | float)
            else parse_base_expression_from_api(minimal_range.lower)
        ),
        max=(
            Constant(minimal_range.upper)
            if isinstance(minimal_range.upper, int | float)
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


def _parse_graph_from_api(
    id_: str,
    graph: graphs_api.Graph,
    registered_metrics: Mapping[str, RegisteredMetric],
    *,
    mirrored: bool,
) -> GraphTemplate:
    metrics: list[MetricExpression] = []
    scalars: list[MetricExpression] = []

    for line in graph.compound_lines:
        if (
            parsed := parse_expression_from_api(
                line,
                "-stack" if mirrored else "stack",
                registered_metrics,
            )
        ).is_scalar():
            scalars.append(parsed)
        else:
            metrics.append(parsed)

    for line in graph.simple_lines:
        if (
            parsed := parse_expression_from_api(
                line,
                "-line" if mirrored else "line",
                registered_metrics,
            )
        ).is_scalar():
            scalars.append(parsed)
        else:
            metrics.append(parsed)

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
    id_: str,
    bidirectional: graphs_api.Bidirectional,
    registered_metrics: Mapping[str, RegisteredMetric],
) -> GraphTemplate:
    upper = _parse_graph_from_api(
        bidirectional.upper.name,
        bidirectional.upper,
        registered_metrics,
        mirrored=False,
    )
    lower = _parse_graph_from_api(
        bidirectional.lower.name,
        bidirectional.lower,
        registered_metrics,
        mirrored=True,
    )

    ranges_min = []
    ranges_max = []
    if upper.range is not None:
        ranges_min.append(upper.range.min)
        ranges_max.append(upper.range.max)

    if lower.range is not None:
        ranges_min.append(lower.range.min)
        ranges_max.append(lower.range.max)

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
        metrics=list(upper.metrics) + list(lower.metrics),
        scalars=list(upper.scalars) + list(lower.scalars),
        optional_metrics=(list(bidirectional.upper.optional) + list(bidirectional.lower.optional)),
        conflicting_metrics=(
            list(bidirectional.upper.conflicting) + list(bidirectional.lower.conflicting)
        ),
        consolidation_function=None,
        omit_zero_metrics=False,
    )


def _parse_graph_plugin(
    id_: str,
    template: graphs_api.Graph | graphs_api.Bidirectional,
    registered_metrics: Mapping[str, RegisteredMetric],
) -> GraphTemplate:
    match template:
        case graphs_api.Graph():
            return _parse_graph_from_api(
                id_,
                template,
                registered_metrics,
                mirrored=False,
            )
        case graphs_api.Bidirectional():
            return _parse_bidirectional_from_api(
                id_,
                template,
                registered_metrics,
            )
        case _:
            assert_never(template)


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


def get_graph_template_from_id(
    template_id: str,
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
) -> GraphTemplate:
    if template_id.startswith("METRIC_"):
        return _create_graph_template_from_name(template_id)
    for id_, graph_plugin in _sort_registered_graph_plugins(registered_graphs):
        if template_id == id_:
            return _parse_graph_plugin(id_, graph_plugin, registered_metrics)
    raise MKGraphNotFound(_("There is no graph plug-in with the id '%s'") % template_id)


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
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
) -> tuple[list[GraphTemplateChoice], list[GraphTemplateChoice]]:
    graph_template_choices = []
    already_graphed_metrics = set()
    for id_, graph_plugin in _sort_registered_graph_plugins(registered_graphs):
        graph_template = _parse_graph_plugin(id_, graph_plugin, registered_metrics)
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
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
) -> tuple[list[GraphTemplateChoice], list[GraphTemplateChoice]]:
    graph_template_choices: list[GraphTemplateChoice] = []
    single_metric_template_choices: list[GraphTemplateChoice] = []

    for row in livestatus_query_bare(
        "service",
        context,
        ["service_check_command", "service_perf_data", "service_metrics"],
    ):
        graph_template_choices_for_row, single_metric_template_choices_for_row = (
            graph_and_single_metric_template_choices_for_metrics(
                translated_metrics_from_row(
                    row,
                    registered_metrics,
                ),
                registered_metrics,
                registered_graphs,
            )
        )
        graph_template_choices.extend(graph_template_choices_for_row)
        single_metric_template_choices.extend(single_metric_template_choices_for_row)

    return graph_template_choices, single_metric_template_choices


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
            operation=evaluated.base.to_metric_operation(
                site_id,
                host_name,
                service_name,
                translated_metrics,
                graph_template.consolidation_function,
            ),
            unit=evaluated.unit_spec,
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
        unit_spec=units.pop(),
        explicit_vertical_range=evaluate_graph_template_range(
            graph_template.range,
            translated_metrics,
        ),
        horizontal_rules=graph_template.horizontal_rules,
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
    # Note: This is not officially supported and only has to work for our internal needs:
    # CPU load, CPU utilization
    for serialized_expression in extract_raw_expressions_from_graph_title(title):
        evaluated_expression = _graph_title_expression_to_metric_expression(
            _GraphTitleExpression.model_validate_json(serialized_expression[len("_EXPRESSION:") :])
        ).evaluate(translated_metrics)
        if evaluated_expression.is_ok():
            title = title.replace(
                serialized_expression,
                str(
                    # rendering as an integer is hard-coded because it is all we need for now
                    int(evaluated_expression.ok.value)
                ),
                1,
            )
        else:
            return title.split("-")[0].strip()
    return title


def extract_raw_expressions_from_graph_title(title: str) -> list[str]:
    return re.findall(r"_EXPRESSION:\{.*?\}", title)


class _GraphTitleExpression(BaseModel, frozen=True):
    metric: str
    scalar: Literal["warn", "crit", "min", "max"]


def _graph_title_expression_to_metric_expression(
    expression: _GraphTitleExpression,
) -> BaseMetricExpression:
    metric = Metric(expression.metric, consolidation=None)
    scalar: BaseMetricExpression
    match expression.scalar:
        case "warn":
            scalar = WarningOf(metric)
        case "crit":
            scalar = CriticalOf(metric)
        case "min":
            scalar = MinimumOf(metric)
        case "max":
            scalar = MaximumOf(metric)
        case _:
            assert_never(expression.scalar)
    return scalar


def _evaluate_scalars(
    metric_expressions: Sequence[MetricExpression],
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Sequence[HorizontalRule]:
    results = []
    for metric_expression in metric_expressions:
        if (result := metric_expression.evaluate(translated_metrics)).is_error():
            # Scalar value like min and max are always optional. This makes configuration
            # of graphs easier.
            if result.error.metric_name:
                continue
            return []
        results.append(
            HorizontalRule(
                value=result.ok.value * (-1 if result.ok.line_type.startswith("-") else 1),
                rendered_value=user_specific_unit(
                    result.ok.unit_spec,
                    user,
                    active_config,
                ).formatter.render(result.ok.value),
                color=result.ok.color,
                title=result.ok.title,
            )
        )
    return results


@dataclass(frozen=True)
class EvaluatedGraphTemplate:
    id: str
    title: str
    horizontal_rules: Sequence[HorizontalRule]
    consolidation_function: GraphConsolidationFunction
    range: FixedGraphTemplateRange | MinimalGraphTemplateRange | None
    omit_zero_metrics: bool
    metrics: Sequence[Evaluated]


def _create_evaluated_graph_template_from_name(
    name: str,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> EvaluatedGraphTemplate:
    if name.startswith("METRIC_"):
        name = name[7:]

    if translated_metric := translated_metrics.get(name):
        return EvaluatedGraphTemplate(
            id=f"METRIC_{name}",
            title="",
            metrics=[
                Evaluated(
                    base=Metric(name),
                    value=translated_metric.value,
                    unit_spec=translated_metric.unit_spec,
                    color=translated_metric.color,
                    line_type="area",
                    title=translated_metric.title,
                )
            ],
            horizontal_rules=compute_warn_crit_rules_from_translated_metric(
                user_specific_unit(translated_metric.unit_spec, user, active_config),
                translated_metric,
            ),
            consolidation_function="max",
            range=None,
            omit_zero_metrics=False,
        )

    return EvaluatedGraphTemplate(
        id=f"METRIC_{name}",
        title="",
        metrics=[],
        horizontal_rules=[],
        consolidation_function="max",
        range=None,
        omit_zero_metrics=False,
    )


def _get_evaluated_graph_templates(
    translated_metrics: Mapping[str, TranslatedMetric],
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
) -> Iterator[EvaluatedGraphTemplate]:
    if not translated_metrics:
        yield from ()
        return

    already_graphed_metrics = set()
    for id_, graph_plugin in _sort_registered_graph_plugins(registered_graphs):
        graph_template = _parse_graph_plugin(id_, graph_plugin, registered_metrics)
        if evaluated_metrics := evaluate_metrics(
            conflicting_metrics=graph_template.conflicting_metrics,
            optional_metrics=graph_template.optional_metrics,
            metric_expressions=graph_template.metrics,
            translated_metrics=translated_metrics,
        ):
            evaluated_graph_template = EvaluatedGraphTemplate(
                id=graph_template.id,
                title=_evaluate_title(graph_template.title, translated_metrics),
                horizontal_rules=_evaluate_scalars(graph_template.scalars, translated_metrics),
                consolidation_function=graph_template.consolidation_function or "max",
                range=graph_template.range,
                omit_zero_metrics=graph_template.omit_zero_metrics,
                metrics=list(
                    itertools.chain(
                        evaluated_metrics,
                        _evaluate_predictive_metrics(evaluated_metrics, translated_metrics),
                    )
                ),
            )
            already_graphed_metrics.update(
                {n for e in evaluated_graph_template.metrics for n in e.metric_names()}
            )
            yield evaluated_graph_template

    for metric_name, translated_metric in sorted(translated_metrics.items()):
        if translated_metric.auto_graph and metric_name not in already_graphed_metrics:
            yield _create_evaluated_graph_template_from_name(metric_name, translated_metrics)


def _matching_graph_templates(
    *,
    graph_id: str | None,
    graph_index: int | None,
    translated_metrics: Mapping[str, TranslatedMetric],
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
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
        yield (0, _create_evaluated_graph_template_from_name(graph_id, translated_metrics))
        return

    yield from (
        (index, graph_template)
        for index, graph_template in enumerate(
            _get_evaluated_graph_templates(
                translated_metrics,
                registered_metrics,
                registered_graphs,
            )
        )
        if (graph_index is None or index == graph_index)
        and (graph_id is None or graph_template.id == graph_id)
    )


class TemplateGraphSpecification(GraphSpecification, frozen=True):
    site: SiteId | None
    host_name: AnnotatedHostName
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

    def recipes(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
        registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
    ) -> list[GraphRecipe]:
        row = self._get_graph_data_from_livestatus()
        translated_metrics = translated_metrics_from_row(row, registered_metrics)
        return [
            recipe
            for index, graph_template in _matching_graph_templates(
                graph_id=self.graph_id,
                graph_index=self.graph_index,
                translated_metrics=translated_metrics,
                registered_metrics=registered_metrics,
                registered_graphs=registered_graphs,
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

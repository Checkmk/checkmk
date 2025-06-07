#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import assert_never, ClassVar, Literal

from livestatus import SiteId

from cmk.utils import pnp_cleanup, regex
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.gui.i18n import _
from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import Row

from ._expression import (
    Average,
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
    parse_expression,
    Product,
    Sum,
    WarningOf,
)
from ._graph_specification import (
    FixedVerticalRange,
    GraphMetric,
    GraphRecipe,
    GraphSpecification,
    HorizontalRule,
    MetricOpConstant,
    MetricOpConstantNA,
    MetricOperation,
    MetricOpOperator,
    MetricOpRRDSource,
    MinimalVerticalRange,
)
from ._type_defs import GraphConsoldiationFunction, TranslatedMetric
from ._utils import (
    FixedGraphTemplateRange,
    get_graph_data_from_livestatus,
    get_graph_templates,
    GraphTemplate,
    MetricDefinition,
    MinimalGraphTemplateRange,
    ScalarDefinition,
    translated_metrics_from_row,
)


class TemplateGraphSpecification(GraphSpecification, frozen=True):
    # Overwritten in cmk/gui/graphing/cee/__init__.py
    TUNE_GRAPH_TEMPLATE: ClassVar[
        Callable[[GraphTemplate, TemplateGraphSpecification], GraphTemplate | None]
    ] = lambda graph_template, _spec: graph_template

    graph_type: Literal["template"] = "template"
    site: SiteId | None
    host_name: HostName
    service_description: ServiceName
    graph_index: int | None = None
    graph_id: str | None = None
    destination: str | None = None

    @staticmethod
    def name() -> str:
        return "template_graph_specification"

    def recipes(self) -> list[GraphRecipe]:
        row = get_graph_data_from_livestatus(self.site, self.host_name, self.service_description)
        translated_metrics = translated_metrics_from_row(row)
        return [
            recipe
            for index, graph_template in matching_graph_templates(
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
            graph_template_tuned,
            translated_metrics,
            row,
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
def matching_graph_templates(
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
        yield (0, GraphTemplate.from_name(graph_id))
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
            result = parse_expression(m.group()[2:-1], translated_metrics).evaluate(
                translated_metrics
            )
        except (ValueError, KeyError):
            return text.split("-")[0].strip()
        return reg.sub(result.unit_info["render"](result.value).strip(), text)

    return text


def _horizontal_rules_from_thresholds(
    thresholds: Iterable[ScalarDefinition],
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Sequence[HorizontalRule]:
    horizontal_rules = []
    for entry in thresholds:
        try:
            if (result := entry.expression.evaluate(translated_metrics)).value:
                horizontal_rules.append(
                    HorizontalRule(
                        result.value * (-1 if entry.mirrored else 1),
                        result.unit_info["render"](result.value),
                        result.color,
                        entry.title,
                    )
                )
        # Scalar value like min and max are always optional. This makes configuration
        # of graphs easier.
        except Exception:
            pass

    return horizontal_rules


def create_graph_recipe_from_template(
    graph_template: GraphTemplate,
    translated_metrics: Mapping[str, TranslatedMetric],
    row: Row,
    specification: GraphSpecification,
) -> GraphRecipe:
    def _graph_metric(metric_definition: MetricDefinition) -> GraphMetric:
        unit_color = metric_definition.compute_unit_color(
            translated_metrics,
            graph_template.optional_metrics,
        )
        return GraphMetric(
            title=metric_definition.compute_title(translated_metrics),
            line_type=metric_definition.line_type,
            operation=metric_expression_to_graph_recipe_expression(
                metric_definition.expression,
                translated_metrics,
                row,
                graph_template.consolidation_function or "max",
            ),
            unit=unit_color["unit"] if unit_color else "",
            color=unit_color["color"] if unit_color else "#000000",
            visible=True,
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
    boundary: MetricExpression, translated_metrics: Mapping[str, TranslatedMetric]
) -> float | None:
    try:
        return boundary.evaluate(translated_metrics).value
    except Exception:
        return None


def _to_metric_operation(  # pylint: disable=too-many-branches
    expression: MetricExpression,
    translated_metrics: Mapping[str, TranslatedMetric],
    lq_row: Row,
    enforced_consolidation_function: GraphConsoldiationFunction | None,
) -> MetricOperation:
    if isinstance(expression, Constant):
        return MetricOpConstant(value=float(expression.value))
    if isinstance(expression, Metric):
        metrics = [
            MetricOpRRDSource(
                site_id=lq_row["site"],
                host_name=lq_row["host_name"],
                service_name=lq_row.get("service_description", "_HOST_"),
                metric_name=pnp_cleanup(orig_name),
                consolidation_func_name=(
                    expression.consolidation_func_name or enforced_consolidation_function
                ),
                scale=scale,
            )
            for orig_name, scale in zip(
                translated_metrics[expression.name]["orig_name"],
                translated_metrics[expression.name]["scale"],
            )
        ]
        if len(metrics) > 1:
            return MetricOpOperator(operator_name="MERGE", operands=metrics)
        return metrics[0]
    if isinstance(expression, Sum):
        return MetricOpOperator(
            operator_name="+",
            operands=[
                _to_metric_operation(
                    s,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for s in expression.summands
            ],
        )
    if isinstance(expression, Product):
        return MetricOpOperator(
            operator_name="*",
            operands=[
                _to_metric_operation(
                    f,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for f in expression.factors
            ],
        )
    if isinstance(expression, Difference):
        return MetricOpOperator(
            operator_name="-",
            operands=[
                _to_metric_operation(
                    expression.minuend,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                ),
                _to_metric_operation(
                    expression.subtrahend,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                ),
            ],
        )
    if isinstance(expression, Fraction):
        return MetricOpOperator(
            operator_name="/",
            operands=[
                _to_metric_operation(
                    expression.dividend,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                ),
                _to_metric_operation(
                    expression.divisor,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                ),
            ],
        )
    if isinstance(expression, Maximum):
        return MetricOpOperator(
            operator_name="MAX",
            operands=[
                _to_metric_operation(
                    o,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for o in expression.operands
            ],
        )
    if isinstance(expression, Minimum):
        return MetricOpOperator(
            operator_name="MIN",
            operands=[
                _to_metric_operation(
                    o,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for o in expression.operands
            ],
        )
    if isinstance(expression, Average):
        return MetricOpOperator(
            operator_name="AVERAGE",
            operands=[
                _to_metric_operation(
                    o,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for o in expression.operands
            ],
        )
    if isinstance(expression, Merge):
        return MetricOpOperator(
            operator_name="MERGE",
            operands=[
                _to_metric_operation(
                    o,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for o in expression.operands
            ],
        )
    if isinstance(expression, (MaximumOf | MinimumOf | WarningOf | CriticalOf)):
        try:
            evaluation_result = expression.evaluate(translated_metrics)
        except KeyError:
            return MetricOpConstantNA()
        return MetricOpConstant(value=float(evaluation_result.value))
    raise TypeError(expression)


def metric_expression_to_graph_recipe_expression(
    metric_expression: MetricExpression,
    translated_metrics: Mapping[str, TranslatedMetric],
    lq_row: Row,
    enforced_consolidation_function: GraphConsoldiationFunction | None,
) -> MetricOperation:
    return _to_metric_operation(
        metric_expression,
        translated_metrics,
        lq_row,
        enforced_consolidation_function,
    )

#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from typing import Final

from livestatus import SiteId

from cmk.utils import pnp_cleanup
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.gui.i18n import _
from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import Row, TranslatedMetrics

from ._expression import (
    Average,
    ConstantFloat,
    ConstantInt,
    Difference,
    Fraction,
    Maximum,
    Merge,
    Metric,
    MetricDeclaration,
    MetricExpression,
    Minimum,
    parse_expression,
    Product,
    Sum,
)
from ._graph_specification import (
    GraphMetric,
    MetricDefinition,
    MetricOpConstant,
    MetricOpOperator,
    MetricOpRRDSource,
    TemplateGraphSpecification,
)
from ._type_defs import GraphConsoldiationFunction
from ._utils import (
    get_graph_data_from_livestatus,
    get_graph_range,
    get_graph_template,
    get_graph_templates,
    GraphRecipe,
    GraphRecipeBase,
    GraphTemplate,
    horizontal_rules_from_thresholds,
    MetricUnitColor,
    replace_expressions,
    translated_metrics_from_row,
)


class TemplateGraphRecipeBuilder:
    def __init__(self) -> None:
        self.graph_type: Final = "template"

    def __call__(self, spec: TemplateGraphSpecification) -> list[GraphRecipe]:
        row = get_graph_data_from_livestatus(spec.site, spec.host_name, spec.service_description)
        translated_metrics = translated_metrics_from_row(row)
        return [
            recipe
            for index, graph_template in matching_graph_templates(
                graph_id=spec.graph_id,
                graph_index=spec.graph_index,
                translated_metrics=translated_metrics,
            )
            if (
                recipe := self._build_recipe_from_template(
                    spec=spec,
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
        spec: TemplateGraphSpecification,
        graph_template: GraphTemplate,
        row: Row,
        translated_metrics: TranslatedMetrics,
        index: int,
    ) -> GraphRecipe | None:
        if not (
            graph_template_tuned := self._template_tuning(
                graph_template,
                site=spec.site,
                host_name=spec.host_name,
                service_description=spec.service_description,
                destination=spec.destination,
            )
        ):
            return None

        graph_recipe = create_graph_recipe_from_template(
            graph_template_tuned,
            translated_metrics,
            row,
        )

        return GraphRecipe(
            title=graph_recipe.title,
            metrics=graph_recipe.metrics,
            unit=graph_recipe.unit,
            explicit_vertical_range=graph_recipe.explicit_vertical_range,
            horizontal_rules=graph_recipe.horizontal_rules,
            omit_zero_metrics=graph_recipe.omit_zero_metrics,
            consolidation_function=graph_recipe.consolidation_function,
            specification=TemplateGraphSpecification(
                site=spec.site,
                host_name=spec.host_name,
                service_description=spec.service_description,
                destination=spec.destination,
                # Performance graph dashlets already use graph_id, but for example in reports, we still
                # use graph_index. We should switch to graph_id everywhere (CMK-7308). Once this is
                # done, we can remove the line below.
                graph_index=index,
                graph_id=graph_template_tuned.id,
            ),
        )

    @staticmethod
    def _template_tuning(
        graph_template: GraphTemplate,
        site: SiteId | None,
        host_name: HostName | None,
        service_description: ServiceName | None,
        destination: str | None,
    ) -> GraphTemplate | None:
        return graph_template


# Performance graph dashlets already use graph_id, but for example in reports, we still use
# graph_index. Therefore, this function needs to support both. We should switch to graph_id
# everywhere (CMK-7308) and remove the support for graph_index. However, note that we cannot easily
# build a corresponding transform, so even after switching to graph_id everywhere, we will need to
# keep this functionality here for some time to support already created dashlets, reports etc.
def matching_graph_templates(
    *,
    graph_id: str | None,
    graph_index: int | None,
    translated_metrics: TranslatedMetrics,
) -> Iterable[tuple[int, GraphTemplate]]:
    # Single metrics
    if (
        isinstance(graph_id, str)
        and graph_id.startswith("METRIC_")
        and graph_id[7:] in translated_metrics
    ):
        yield (0, get_graph_template(graph_id))
        return

    yield from (
        (index, graph_template)
        for index, graph_template in enumerate(get_graph_templates(translated_metrics))
        if (graph_index is None or index == graph_index)
        and (graph_id is None or graph_template.id == graph_id)
    )


def create_graph_recipe_from_template(
    graph_template: GraphTemplate, translated_metrics: TranslatedMetrics, row: Row
) -> GraphRecipeBase:
    def _metric(metric_definition: MetricDefinition) -> GraphMetric:
        metric_expression = parse_expression(
            metric_definition.expression,
            translated_metrics,
            graph_template.consolidation_function or "max",
        )
        unit_color = metric_unit_color(metric_expression, translated_metrics)
        return GraphMetric(
            title=metric_line_title(metric_definition, metric_expression, translated_metrics),
            line_type=metric_definition.line_type,
            expression=metric_expression_to_graph_recipe_expression(
                metric_expression,
                translated_metrics,
                row,
                graph_template.consolidation_function or "max",
            ),
            unit=unit_color["unit"] if unit_color else "",
            color=unit_color["color"] if unit_color else "#000000",
            visible=True,
        )

    metrics = list(map(_metric, graph_template.metrics))
    units = {m.unit for m in metrics}
    if len(units) > 1:
        raise MKGeneralException(
            _("Cannot create graph with metrics of different units '%s'") % ", ".join(units)
        )

    title = replace_expressions(graph_template.title or "", translated_metrics)
    if not title:
        title = next((m.title for m in metrics), "")

    painter_options = PainterOptions.get_instance()
    if painter_options.get("show_internal_graph_and_metric_ids"):
        title = title + f" (Graph ID: {graph_template.id})"

    return GraphRecipeBase(
        title=title,
        metrics=metrics,
        unit=units.pop(),
        explicit_vertical_range=get_graph_range(graph_template, translated_metrics),
        horizontal_rules=horizontal_rules_from_thresholds(
            graph_template.scalars, translated_metrics
        ),  # e.g. lines for WARN and CRIT
        omit_zero_metrics=graph_template.omit_zero_metrics,
        consolidation_function=graph_template.consolidation_function or "max",
    )


def _to_metric_operation(
    declaration: MetricDeclaration,
    translated_metrics: TranslatedMetrics,
    lq_row: Row,
    enforced_consolidation_function: GraphConsoldiationFunction | None,
) -> MetricOpRRDSource | MetricOpOperator | MetricOpConstant:
    if isinstance(declaration, (ConstantInt, ConstantFloat)):
        return MetricOpConstant(value=declaration.value)
    if isinstance(declaration, Metric):
        return MetricOpRRDSource(
            site_id=lq_row["site"],
            host_name=lq_row["host_name"],
            service_name=lq_row.get("service_description", "_HOST_"),
            metric_name=pnp_cleanup(translated_metrics[declaration.name]["orig_name"][0]),
            consolidation_func_name=(
                declaration.consolidation_func_name or enforced_consolidation_function
            ),
            scale=translated_metrics[declaration.name]["scale"][0],
        )
    if isinstance(declaration, Sum):
        return MetricOpOperator(
            operator_name="+",
            operands=[
                _to_metric_operation(
                    s,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for s in declaration.summands
            ],
        )
    if isinstance(declaration, Product):
        return MetricOpOperator(
            operator_name="*",
            operands=[
                _to_metric_operation(
                    f,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for f in declaration.factors
            ],
        )
    if isinstance(declaration, Difference):
        return MetricOpOperator(
            operator_name="-",
            operands=[
                _to_metric_operation(
                    declaration.minuend,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                ),
                _to_metric_operation(
                    declaration.subtrahend,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                ),
            ],
        )
    if isinstance(declaration, Fraction):
        return MetricOpOperator(
            operator_name="/",
            operands=[
                _to_metric_operation(
                    declaration.dividend,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                ),
                _to_metric_operation(
                    declaration.divisor,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                ),
            ],
        )
    if isinstance(declaration, Maximum):
        return MetricOpOperator(
            operator_name="MAX",
            operands=[
                _to_metric_operation(
                    o,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for o in declaration.operands
            ],
        )
    if isinstance(declaration, Minimum):
        return MetricOpOperator(
            operator_name="MIN",
            operands=[
                _to_metric_operation(
                    o,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for o in declaration.operands
            ],
        )
    if isinstance(declaration, Average):
        return MetricOpOperator(
            operator_name="AVERAGE",
            operands=[
                _to_metric_operation(
                    o,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for o in declaration.operands
            ],
        )
    if isinstance(declaration, Merge):
        return MetricOpOperator(
            operator_name="MERGE",
            operands=[
                _to_metric_operation(
                    o,
                    translated_metrics,
                    lq_row,
                    enforced_consolidation_function,
                )
                for o in declaration.operands
            ],
        )
    raise TypeError(declaration)


def metric_expression_to_graph_recipe_expression(
    metric_expression: MetricExpression,
    translated_metrics: TranslatedMetrics,
    lq_row: Row,
    enforced_consolidation_function: GraphConsoldiationFunction | None,
) -> MetricOpRRDSource | MetricOpOperator | MetricOpConstant:
    return _to_metric_operation(
        metric_expression.declaration,
        translated_metrics,
        lq_row,
        enforced_consolidation_function,
    )


def metric_line_title(
    metric_definition: MetricDefinition,
    metric_expression: MetricExpression,
    translated_metrics: TranslatedMetrics,
) -> str:
    if metric_definition.title:
        return metric_definition.title
    return translated_metrics[next(metric_expression.metrics()).name]["title"]


def metric_unit_color(
    metric_expression: MetricExpression,
    translated_metrics: TranslatedMetrics,
    optional_metrics: Sequence[str] | None = None,
) -> MetricUnitColor | None:
    try:
        result = metric_expression.evaluate(translated_metrics)
    except KeyError as err:  # because metric_name is not in translated_metrics
        metric_name = err.args[0]
        if optional_metrics and metric_name in optional_metrics:
            return None
        raise MKGeneralException(
            _("Graph recipe '%s' uses undefined metric '%s', available are: %s")
            % (
                metric_expression,
                metric_name,
                ", ".join(sorted(translated_metrics.keys())) or "None",
            )
        )
    return {"unit": result.unit_info["id"], "color": result.color}

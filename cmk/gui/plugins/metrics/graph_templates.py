#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Iterator, Sequence
from typing import Final

from livestatus import SiteId

from cmk.utils import pnp_cleanup
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.painter_options import PainterOptions
from cmk.gui.plugins.metrics.identification import GraphIdentification
from cmk.gui.plugins.metrics.utils import (
    evaluate,
    get_graph_data_from_livestatus,
    get_graph_range,
    get_graph_template,
    get_graph_templates,
    GraphRecipeBase,
    GraphTemplate,
    horizontal_rules_from_thresholds,
    metrics_used_in_expression,
    MetricUnitColor,
    replace_expressions,
    split_expression,
    stack_resolver,
    TemplateGraphRecipe,
    translated_metrics_from_row,
)
from cmk.gui.type_defs import (
    GraphConsoldiationFunction,
    GraphMetric,
    MetricDefinition,
    MetricExpression,
    Row,
    RPNExpression,
    TemplateGraphSpec,
    TranslatedMetrics,
)
from cmk.gui.utils.graph_specification import TemplateGraphSpecification

from .graph_recipe_builder import graph_recipe_builder_registry


class TemplateGraphRecipeBuilder:
    def __init__(self) -> None:
        self.graph_type: Final = "template"

    def __call__(self, spec: TemplateGraphSpecification) -> list[TemplateGraphRecipe]:
        row = get_graph_data_from_livestatus(spec.site, spec.host_name, spec.service_description)
        translated_metrics = translated_metrics_from_row(row)
        return [
            recipe
            for index, graph_template in matching_graph_templates(
                spec.to_legacy_format(),
                translated_metrics,
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
    ) -> TemplateGraphRecipe | None:
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

        spec_info = spec.to_legacy_format()
        # Performance graph dashlets already use graph_id, but for example in reports, we still
        # use graph_index. We should switch to graph_id everywhere (CMK-7308). Once this is
        # done, we can remove the line below.
        spec_info["graph_index"] = index
        spec_info["graph_id"] = graph_template_tuned["id"]

        return TemplateGraphRecipe(
            title=graph_recipe["title"],
            metrics=graph_recipe["metrics"],
            unit=graph_recipe["unit"],
            explicit_vertical_range=graph_recipe["explicit_vertical_range"],
            horizontal_rules=graph_recipe["horizontal_rules"],
            omit_zero_metrics=graph_recipe["omit_zero_metrics"],
            consolidation_function=graph_recipe["consolidation_function"],
            specification=("template", spec_info),
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


graph_recipe_builder_registry.register(TemplateGraphRecipeBuilder())


# Performance graph dashlets already use graph_id, but for example in reports, we still use
# graph_index. Therefore, this function needs to support both. We should switch to graph_id
# everywhere (CMK-7308) and remove the support for graph_index. However, note that we cannot easily
# build a corresponding transform, so even after switching to graph_id everywhere, we will need to
# keep this functionality here for some time to support already created dashlets, reports etc.
def matching_graph_templates(
    graph_identification_info: TemplateGraphSpec,
    translated_metrics: TranslatedMetrics,
) -> Iterable[tuple[int, GraphTemplate]]:
    graph_index = graph_identification_info.get(
        "graph_index"
    )  # can be None -> no restriction by index
    graph_id = graph_identification_info.get("graph_id")  # can be None -> no restriction by id

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
        and (graph_id is None or graph_template["id"] == graph_id)
    )


class GraphIdentificationTemplate(GraphIdentification[TemplateGraphSpec, TemplateGraphRecipe]):
    @classmethod
    def ident(cls) -> str:
        return "template"

    @staticmethod
    def template_tuning(
        graph_template: GraphTemplate,
        site: str | None,
        host_name: HostName | None,
        service_description: ServiceName | None,
        destination: str | None,
    ) -> GraphTemplate | None:
        return graph_template

    def create_graph_recipes(
        self, ident_info: TemplateGraphSpec, destination: str | None = None
    ) -> list[TemplateGraphRecipe]:
        graph_identification_info = ident_info

        try:
            site = graph_identification_info["site"]
            host_name = graph_identification_info["host_name"]
            service_description = graph_identification_info["service_description"]
        except KeyError as e:
            raise MKUserError(None, _("Graph identification: The '%s' attribute is missing") % e)
        row = get_graph_data_from_livestatus(site, host_name, service_description)
        translated_metrics = translated_metrics_from_row(row)

        graph_recipes = []
        for index, graph_template in matching_graph_templates(
            graph_identification_info,
            translated_metrics,
        ):
            graph_template_tuned = self.template_tuning(
                graph_template,
                site=site,
                host_name=host_name,
                service_description=service_description,
                destination=destination,
            )
            if graph_template_tuned is None:
                continue

            graph_recipe = create_graph_recipe_from_template(
                graph_template_tuned,
                translated_metrics,
                row,
            )

            spec_info = graph_identification_info.copy()
            # Performance graph dashlets already use graph_id, but for example in reports, we still
            # use graph_index. We should switch to graph_id everywhere (CMK-7308). Once this is
            # done, we can remove the line below.
            spec_info["graph_index"] = index
            spec_info["graph_id"] = graph_template_tuned["id"]

            graph_recipes.append(
                TemplateGraphRecipe(
                    {
                        "title": graph_recipe["title"],
                        "metrics": graph_recipe["metrics"],
                        "unit": graph_recipe["unit"],
                        "explicit_vertical_range": graph_recipe["explicit_vertical_range"],
                        "horizontal_rules": graph_recipe["horizontal_rules"],
                        "omit_zero_metrics": graph_recipe["omit_zero_metrics"],
                        "consolidation_function": graph_recipe["consolidation_function"],
                        "specification": ("template", spec_info),
                    }
                )
            )
        return graph_recipes


def create_graph_recipe_from_template(
    graph_template: GraphTemplate, translated_metrics: TranslatedMetrics, row: Row
) -> GraphRecipeBase:
    def _metric(metric_definition: MetricDefinition) -> GraphMetric:
        metric = GraphMetric(
            {
                "title": metric_line_title(metric_definition, translated_metrics),
                "line_type": metric_definition[1],
                "expression": metric_expression_to_graph_recipe_expression(
                    metric_definition[0],
                    translated_metrics,
                    row,
                    graph_template.get("consolidation_function", "max"),
                ),
            }
        )

        unit_color = metric_unit_color(metric_definition[0], translated_metrics)
        if unit_color:
            metric.update(
                {
                    "color": unit_color["color"],
                    "unit": unit_color["unit"],
                }
            )
        return metric

    metrics = list(map(_metric, graph_template["metrics"]))
    units = {m["unit"] for m in metrics}
    if len(units) > 1:
        raise MKGeneralException(
            _("Cannot create graph with metrics of different units '%s'") % ", ".join(units)
        )

    title = replace_expressions(str(graph_template.get("title", "")), translated_metrics)
    if not title:
        title = next((m["title"] for m in metrics if m["title"]), "")

    painter_options = PainterOptions.get_instance()
    if painter_options.get("show_internal_graph_and_metric_ids"):
        title = title + f" (Graph ID: {graph_template['id']})"

    return {
        "title": title,
        "metrics": metrics,
        "unit": units.pop(),
        "explicit_vertical_range": get_graph_range(graph_template, translated_metrics),
        "horizontal_rules": horizontal_rules_from_thresholds(
            graph_template.get("scalars", []), translated_metrics
        ),  # e.g. lines for WARN and CRIT
        "omit_zero_metrics": graph_template.get("omit_zero_metrics", False),
        "consolidation_function": graph_template.get("consolidation_function", "max"),
    }


def iter_rpn_expression(
    expression: MetricExpression,
    enforced_consolidation_function: GraphConsoldiationFunction | None,
) -> Iterator[tuple[str, GraphConsoldiationFunction | None]]:
    for part in expression.split(","):  # var names, operators
        if any(part.endswith(cf) for cf in [".max", ".min", ".average"]):
            part, raw_consolidation_function = part.rsplit(".", 1)
            if (
                enforced_consolidation_function is not None
                and raw_consolidation_function != enforced_consolidation_function
            ):
                raise MKGeneralException(
                    _(
                        'The expression "%s" uses a different consolidation '
                        "function as the graph (%s). This is not allowed."
                    )
                    % (expression, enforced_consolidation_function)
                )

            # A bit verbose here, but we want to keep the Literal type. Find a better way, please.
            consolidation_function: GraphConsoldiationFunction
            if raw_consolidation_function == "max":
                consolidation_function = "max"
            elif raw_consolidation_function == "min":
                consolidation_function = "min"
            elif raw_consolidation_function == "average":
                consolidation_function = "average"
            else:
                raise ValueError()

            yield part, consolidation_function
        else:
            yield part, enforced_consolidation_function


def metric_expression_to_graph_recipe_expression(
    expression: MetricExpression,
    translated_metrics: TranslatedMetrics,
    lq_row: Row,
    enforced_consolidation_function: GraphConsoldiationFunction | None,
) -> RPNExpression:
    """Convert 'user,util,+,2,*' into this:

        ('operator',
            '*',
            [('operator',
            '+',
            [('rrd',
                'heute',
                u'heute',
                u'CPU utilization',
    ...."""
    rrd_base_element = (
        "rrd",
        lq_row["site"],
        lq_row["host_name"],
        lq_row.get("service_description", "_HOST_"),
    )

    expression = split_expression(expression)[0]
    atoms: list[RPNExpression] = []
    # Break the RPN into parts and translate each part separately
    for part, cf in iter_rpn_expression(expression, enforced_consolidation_function):
        # Some parts are operators. We leave them. We are just interested in
        # names of metrics.
        if part in translated_metrics:  # name of a variable that we know
            tme = translated_metrics[part]
            metric_names = tme.get("orig_name", [part])  # original name before translation
            # We do the replacement of special characters with _ right here.
            # Normally it should be a task of the core. But: We have variables
            # named "/" - which is very silly, but is due to the bogus perf names
            # of the df check. So the CMC could not really distinguish this from
            # the RPN operator /.
            for metric_name, scale in zip(metric_names, tme["scale"]):
                atoms.append(rrd_base_element + (pnp_cleanup(metric_name), cf, scale))
            if len(metric_names) > 1:
                atoms.append(("operator", "MERGE"))

        else:
            try:
                atoms.append(("constant", float(part)))
            except ValueError:
                atoms.append(("operator", part))

    return stack_resolver(
        atoms,
        is_operator=lambda x: x[0] == "operator",
        apply_operator=lambda op, a, b: (op + ([a, b],)),
        apply_element=lambda x: x,
    )


def metric_line_title(
    metric_definition: MetricDefinition, translated_metrics: TranslatedMetrics
) -> str:
    if len(metric_definition) >= 3:
        # mypy does not understand the variable length (Tuple index out of range)
        metric_title = metric_definition[2]  # type: ignore[misc]
        return str(metric_title)

    metric_name = next(metrics_used_in_expression(metric_definition[0]))
    return translated_metrics[metric_name]["title"]


def metric_unit_color(
    metric_expression: MetricExpression,
    translated_metrics: TranslatedMetrics,
    optional_metrics: Sequence[str] | None = None,
) -> MetricUnitColor | None:
    try:
        _value, unit, color = evaluate(metric_expression, translated_metrics)
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
    return {"unit": unit["id"], "color": color}

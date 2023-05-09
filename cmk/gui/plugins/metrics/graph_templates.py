#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple

from cmk.utils import pnp_cleanup

from cmk.gui.exceptions import MKGeneralException, MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.identification import graph_identification_types, GraphIdentification
from cmk.gui.plugins.metrics.utils import (
    evaluate,
    get_graph_data_from_livestatus,
    get_graph_range,
    get_graph_templates,
    GraphRecipe,
    GraphTemplate,
    horizontal_rules_from_thresholds,
    metrics_used_in_expression,
    replace_expressions,
    split_expression,
    stack_resolver,
    translated_metrics_from_row,
    TranslatedMetrics,
)

RPNAtom = Tuple  # TODO: Improve this type


# Performance graph dashlets already use graph_id, but for example in reports, we still use
# graph_index. Therefore, this function needs to support both. We should switch to graph_id
# everywhere (CMK-7308) and remove the support for graph_index. However, note that we cannot easily
# build a corresponding transform, so even after switching to graph_id everywhere, we will need to
# keep this functionality here for some time to support already created dashlets, reports etc.
def matching_graph_templates(
    graph_identification_info: Mapping,
    translated_metrics: TranslatedMetrics,
) -> Iterable[Tuple[int, GraphTemplate]]:
    graph_index = graph_identification_info.get(
        "graph_index")  # can be None -> no restriction by index
    graph_id = graph_identification_info.get("graph_id")  # can be None -> no restriction by id
    yield from ((index, graph_template)
                for index, graph_template in enumerate(get_graph_templates(translated_metrics))
                if (graph_index is None or index == graph_index) and
                (graph_id is None or graph_template["id"] == graph_id))


class GraphIdentificationTemplate(GraphIdentification):
    @classmethod
    def ident(cls) -> str:
        return "template"

    def create_graph_recipes(self, ident_info, destination=None) -> Sequence[GraphRecipe]:
        graph_identification_info = ident_info

        def get_info(key):
            try:
                return graph_identification_info[key]
            except KeyError:
                raise MKUserError(None,
                                  _("Graph identification: The '%s' attribute is missing") % key)

        site = get_info('site')
        host_name = get_info('host_name')
        service_description = get_info('service_description')
        row = get_graph_data_from_livestatus(site, host_name, service_description)
        translated_metrics = translated_metrics_from_row(row)

        graph_recipes = []
        for index, graph_template in matching_graph_templates(
                graph_identification_info,
                translated_metrics,
        ):
            graph_recipe = create_graph_recipe_from_template(
                graph_template,
                translated_metrics,
                row,
            )
            # Put the specification of this graph into the graph_recipe
            spec_info = graph_identification_info.copy()
            # Performance graph dashlets already use graph_id, but for example in reports, we still
            # use graph_index. We should switch to graph_id everywhere (CMK-7308). Once this is
            # done, we can remove the line below.
            spec_info["graph_index"] = index
            spec_info["graph_id"] = graph_template["id"]
            graph_recipe["specification"] = ("template", spec_info)
            graph_recipes.append(graph_recipe)
        return graph_recipes


graph_identification_types.register(GraphIdentificationTemplate)


def create_graph_recipe_from_template(graph_template, translated_metrics, row):
    def _metrics(metric_definition):
        return {
            **metric_unit_color(metric_definition[0], translated_metrics), "title":
                metric_line_title(metric_definition, translated_metrics),
            "line_type": metric_definition[1],
            "expression": metric_expression_to_graph_recipe_expression(
                metric_definition[0], translated_metrics, row,
                graph_template.get("consolidation_function", "max"))
        }

    metrics = list(map(_metrics, graph_template['metrics']))
    units = {m['unit'] for m in metrics}
    if len(units) > 1:
        raise MKGeneralException(
            _("Cannot create graph with metrics of "
              "different units '%s'") % ", ".join(units))

    title = replace_expressions(graph_template.get("title", ""), translated_metrics)
    if not title:
        title = next((m['title'] for m in metrics if m['title']), "")

    return {
        "title": title,
        "metrics": metrics,
        "unit": units.pop(),
        "explicit_vertical_range": get_graph_range(graph_template, translated_metrics),
        "horizontal_rules": horizontal_rules_from_thresholds(graph_template.get(
            "scalars", []), translated_metrics),  # e.g. lines for WARN and CRIT
        "omit_zero_metrics": graph_template.get("omit_zero_metrics", False),
        "consolidation_function": graph_template.get("consolidation_function", "max"),
    }


def iter_rpn_expression(
        expression: str,
        enforced_consolidation_function: Optional[str]) -> Iterator[Tuple[str, Optional[str]]]:
    for part in expression.split(","):  # var names, operators
        if any(part.endswith(cf) for cf in ['.max', '.min', '.average']):
            part, consolidation_function = part.rsplit(".", 1)
            if enforced_consolidation_function is not None and \
                consolidation_function != enforced_consolidation_function:
                raise MKGeneralException(
                    _("The expression \"%s\" uses a different consolidation "
                      "function as the graph (%s). This is not allowed.") %
                    (expression, enforced_consolidation_function))

            yield part, consolidation_function
        else:
            yield part, enforced_consolidation_function


def metric_expression_to_graph_recipe_expression(expression, translated_metrics, lq_row,
                                                 enforced_consolidation_function):
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
    rrd_base_element = ("rrd", lq_row["site"], lq_row["host_name"],
                        lq_row.get('service_description', "_HOST_"))

    expression = split_expression(expression)[0]
    atoms: List[RPNAtom] = []
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

    return stack_resolver(atoms,
                          is_operator=lambda x: x[0] == "operator",
                          apply_operator=lambda op, a, b: (op + ([a, b],)),
                          apply_element=lambda x: x)


def metric_line_title(metric_definition: Tuple, translated_metrics: Dict) -> str:
    if len(metric_definition) >= 3:
        return metric_definition[2]

    metric_name = next(metrics_used_in_expression(metric_definition[0]))
    return translated_metrics[metric_name]["title"]


def metric_unit_color(
    metric_expression: str,
    translated_metrics: TranslatedMetrics,
    optional_metrics=None,
) -> Dict[str, str]:
    try:
        _value, unit, color = evaluate(metric_expression, translated_metrics)
    except KeyError as err:  # because metric_name is not in translated_metrics
        metric_name = err.args[0]
        if optional_metrics and metric_name in optional_metrics:
            return {}
        raise MKGeneralException(
            _("Graph recipe '%s' uses undefined metric '%s', available are: %s") %
            (metric_expression, metric_name, ", ".join(sorted(translated_metrics.keys())) or
             "None"))
    return {"unit": unit["id"], "color": color}

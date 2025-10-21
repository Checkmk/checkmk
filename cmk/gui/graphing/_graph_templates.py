#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Self

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.graphing import v1 as graphing_api
from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api
from cmk.gui.i18n import _, translate_to_current_language
from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import Row
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.utils.servicename import ServiceName

from ._evaluations_from_api import (
    evaluate_graph_plugin_metrics,
    evaluate_graph_plugin_range,
    evaluate_graph_plugin_scalars,
    evaluate_graph_plugin_title,
)
from ._from_api import RegisteredMetric
from ._graph_metric_expressions import (
    AnnotatedHostName,
    create_graph_metric_expression_from_translated_metric,
    GraphConsolidationFunction,
)
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
from ._rrd import get_graph_data_from_livestatus
from ._translated_metrics import translated_metrics_from_row, TranslatedMetric
from ._unit import ConvertibleUnitSpecification, user_specific_unit


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


@dataclass(frozen=True)
class GraphPluginChoice:
    id: str
    title: str


def get_graph_plugin_choices(
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
) -> list[GraphPluginChoice]:
    return sorted(
        [
            GraphPluginChoice(graph.name, graph.title.localize(translate_to_current_language))
            for graph in registered_graphs.values()
        ],
        key=lambda c: c.title,
    )


def get_graph_plugin_from_id(
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
    graph_id: str,
) -> graphs_api.Graph | graphs_api.Bidirectional:
    if graph_id.startswith("METRIC_"):
        metric_name = graph_id[7:]
        return graphs_api.Graph(
            name=graph_id,
            title=graphing_api.Title(""),
            compound_lines=[metric_name],
            simple_lines=[
                metrics_api.WarningOf(metric_name),
                metrics_api.CriticalOf(metric_name),
            ],
        )
    for name, graph_plugin in _sort_registered_graph_plugins(registered_graphs):
        if graph_id == name:
            return graph_plugin
    raise MKGraphNotFound(_("There is no graph plug-in with the id '%s'") % graph_id)


def get_graph_plugin_and_single_metric_choices(
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> tuple[list[GraphPluginChoice], list[GraphPluginChoice]]:
    graph_plugin_choices = []
    already_graphed_metrics: set[str] = set()
    for _graph_id, graph_plugin in _sort_registered_graph_plugins(registered_graphs):
        if (
            graphed_metrics := evaluate_graph_plugin_metrics(
                registered_metrics,
                site_id,
                host_name,
                service_name,
                "max",
                graph_plugin,
                translated_metrics,
            )
        ).graph_metrics:
            already_graphed_metrics.update(graphed_metrics.metric_names)
            graph_plugin_choices.append(
                GraphPluginChoice(
                    graph_plugin.name,
                    graph_plugin.title.localize(translate_to_current_language),
                )
            )

    single_metric_choices = []
    for metric_name, translated_metric in sorted(translated_metrics.items()):
        if translated_metric.auto_graph and metric_name not in already_graphed_metrics:
            single_metric_choices.append(
                GraphPluginChoice(
                    f"METRIC_{metric_name}",
                    _("Metric: %s") % translated_metric.title,
                )
            )
    return graph_plugin_choices, single_metric_choices


def _create_graph_recipe_from_translated_metric(
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    translated_metric: TranslatedMetric,
    specification: TemplateGraphSpecification,
    *,
    temperature_unit: TemperatureUnit,
) -> GraphRecipe:
    title = translated_metric.title
    consolidation_function: Literal["max"] = "max"
    graph_metric = GraphMetric(
        title=title,
        line_type="area",
        operation=create_graph_metric_expression_from_translated_metric(
            site_id,
            host_name,
            service_name,
            translated_metric,
            consolidation_function,
        ),
        unit=translated_metric.unit_spec,
        color=translated_metric.color,
    )
    return GraphRecipe(
        title=title,
        metrics=[graph_metric],
        unit_spec=graph_metric.unit,
        explicit_vertical_range=None,
        horizontal_rules=compute_warn_crit_rules_from_translated_metric(
            user_specific_unit(translated_metric.unit_spec, temperature_unit),
            translated_metric,
        ),
        omit_zero_metrics=False,
        consolidation_function=consolidation_function,
        specification=specification,
    )


def _create_graph_recipe(
    specification: GraphSpecification,
    *,
    title: str,
    graph_metrics: Sequence[GraphMetric],
    explicit_vertical_range: FixedVerticalRange | MinimalVerticalRange | None,
    horizontal_rules: Sequence[HorizontalRule],
    consolidation_function: GraphConsolidationFunction,
) -> GraphRecipe:
    units = {m.unit for m in graph_metrics}

    # We cannot validate the hypothetical case of a mixture of metrics from the legacy and the new API
    if all(isinstance(m.unit, str) for m in graph_metrics) or all(
        isinstance(m.unit, ConvertibleUnitSpecification) for m in graph_metrics
    ):
        if len(units) > 1:
            raise MKGeneralException(
                _("Cannot create graph with metrics of different units '%s'")
                % ", ".join(repr(unit) for unit in units)
            )

    if not title:
        title = next((m.title for m in graph_metrics), "")

    return GraphRecipe(
        title=title,
        metrics=graph_metrics,
        unit_spec=units.pop(),
        explicit_vertical_range=explicit_vertical_range,
        horizontal_rules=horizontal_rules,
        omit_zero_metrics=False,
        consolidation_function=consolidation_function,
        specification=specification,
    )


def _compute_graph_recipes(
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    translated_metrics: Mapping[str, TranslatedMetric],
    specification: TemplateGraphSpecification,
    *,
    temperature_unit: TemperatureUnit,
) -> Iterator[tuple[str, GraphRecipe]]:
    consolidation_function: Literal["max"] = "max"
    already_graphed_metrics: set[str] = set()
    for graph_id, graph_plugin in _sort_registered_graph_plugins(registered_graphs):
        if (
            graphed_metrics := evaluate_graph_plugin_metrics(
                registered_metrics,
                site_id,
                host_name,
                service_name,
                consolidation_function,
                graph_plugin,
                translated_metrics,
            )
        ).graph_metrics:
            already_graphed_metrics.update(graphed_metrics.metric_names)
            yield (
                graph_id,
                _create_graph_recipe(
                    specification,
                    title=evaluate_graph_plugin_title(
                        registered_metrics,
                        graph_plugin.title.localize(translate_to_current_language),
                        translated_metrics,
                    ),
                    graph_metrics=graphed_metrics.graph_metrics,
                    explicit_vertical_range=evaluate_graph_plugin_range(
                        registered_metrics,
                        graph_plugin,
                        translated_metrics,
                    ),
                    horizontal_rules=evaluate_graph_plugin_scalars(
                        registered_metrics,
                        graph_plugin,
                        translated_metrics,
                        temperature_unit=temperature_unit,
                    ),
                    consolidation_function=consolidation_function,
                ),
            )

    for metric_name, translated_metric in sorted(translated_metrics.items()):
        if translated_metric.auto_graph and metric_name not in already_graphed_metrics:
            yield (
                metric_name if metric_name.startswith("METRIC_") else f"METRIC_{metric_name}",
                _create_graph_recipe(
                    specification,
                    title="",
                    graph_metrics=[
                        GraphMetric(
                            title=translated_metric.title,
                            line_type="area",
                            operation=create_graph_metric_expression_from_translated_metric(
                                site_id,
                                host_name,
                                service_name,
                                translated_metric,
                                consolidation_function,
                            ),
                            unit=translated_metric.unit_spec,
                            color=translated_metric.color,
                        )
                    ],
                    explicit_vertical_range=None,
                    horizontal_rules=compute_warn_crit_rules_from_translated_metric(
                        user_specific_unit(translated_metric.unit_spec, temperature_unit),
                        translated_metric,
                    ),
                    consolidation_function=consolidation_function,
                ),
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

    @classmethod
    def _make_specification(
        cls,
        *,
        site: SiteId | None,
        host_name: AnnotatedHostName,
        service_description: ServiceName,
        graph_index: int | None,
        graph_id: str | None,
        destination: str | None,
    ) -> Self:
        return cls(
            site=site,
            host_name=host_name,
            service_description=service_description,
            destination=destination,
            graph_index=graph_index,
            graph_id=graph_id,
        )

    def _post_process_recipe(
        self,
        user_permissions: UserPermissions,
        site_id: SiteId,
        host_name: HostName,
        service_name: ServiceName,
        painter_options: PainterOptions,
        *,
        graph_index: int,
        graph_id: str,
        graph_recipe: GraphRecipe,
    ) -> GraphRecipe | None:
        return GraphRecipe(
            title=(
                f"{graph_recipe.title} (Graph ID: {graph_id})"
                if painter_options.get("show_internal_graph_and_metric_ids")
                else graph_recipe.title
            ),
            unit_spec=graph_recipe.unit_spec,
            explicit_vertical_range=graph_recipe.explicit_vertical_range,
            horizontal_rules=graph_recipe.horizontal_rules,
            omit_zero_metrics=graph_recipe.omit_zero_metrics,
            consolidation_function=graph_recipe.consolidation_function,
            metrics=graph_recipe.metrics,
            specification=self._make_specification(
                site=site_id,
                host_name=self.host_name,
                service_description=self.service_description,
                graph_index=graph_index,
                graph_id=graph_id,
                destination=self.destination,
            ),
        )

    def recipes(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
        registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
        user_permissions: UserPermissions,
        *,
        debug: bool,
        temperature_unit: TemperatureUnit,
    ) -> list[GraphRecipe]:
        row = self._get_graph_data_from_livestatus()
        if not (
            translated_metrics := translated_metrics_from_row(
                row,
                registered_metrics,
                debug=debug,
                temperature_unit=temperature_unit,
            )
        ):
            return []

        site_id = row["site"]
        host_name = row["host_name"]
        service_name = row.get("service_description", "_HOST_")
        painter_options = PainterOptions.get_instance()
        # Performance graph dashlets already use graph_id, but for example in reports, we still use
        # graph_index. Therefore, this function needs to support both. We should switch to graph_id
        # everywhere (CMK-7308) and remove the support for graph_index. However, note that we cannot
        # easily build a corresponding transform, so even after switching to graph_id everywhere, we
        # will need to keep this functionality here for some time to support already created dashlets,
        # reports etc.
        if (
            isinstance(self.graph_id, str)
            and self.graph_id.startswith("METRIC_")
            and self.graph_id[7:] in translated_metrics
        ):
            recipes = [
                (
                    0,
                    self.graph_id,
                    _create_graph_recipe_from_translated_metric(
                        site_id,
                        host_name,
                        service_name,
                        translated_metrics[self.graph_id[7:]],
                        self,  # does not matter here, it will be overwritten in _post_process_recipe
                        temperature_unit=temperature_unit,
                    ),
                )
            ]
        else:
            recipes = [
                (graph_recipe_index, graph_recipe_id, graph_recipe)
                for graph_recipe_index, (graph_recipe_id, graph_recipe) in enumerate(
                    _compute_graph_recipes(
                        registered_metrics,
                        registered_graphs,
                        site_id,
                        host_name,
                        service_name,
                        translated_metrics,
                        self,  # does not matter here, it will be overwritten in _post_process_recipe
                        temperature_unit=temperature_unit,
                    )
                )
                if (self.graph_index is None or self.graph_index == graph_recipe_index)
                and (self.graph_id is None or self.graph_id == graph_recipe_id)
            ]
        return [
            post_processed_recipe
            for graph_index, graph_id, graph_recipe in recipes
            if (
                post_processed_recipe := self._post_process_recipe(
                    user_permissions,
                    site_id,
                    host_name,
                    service_name,
                    painter_options,
                    graph_index=graph_index,
                    graph_id=graph_id,
                    graph_recipe=graph_recipe,
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

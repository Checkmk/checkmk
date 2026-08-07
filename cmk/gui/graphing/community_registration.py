#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.ccc.version import Edition
from cmk.gui.autocompleters import AutocompleterRegistry
from cmk.gui.form_specs.unstable import MetricExtended
from cmk.gui.form_specs.visitors import register_visitor_class
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.type_defs import Choices
from cmk.gui.watolib.config_domain_name import ConfigVariableRegistry

from ._autocompleter import metrics_autocompleter
from ._engine_codec import community_graph_codec, GraphCodec
from ._engine_dispatch import graph_dispatcher_registry, GraphDispatcherRegistry
from ._engine_template_graphs import template_graph_dispatcher
from ._explicit_graphs import ExplicitGraphSpecification
from ._graph_images import AjaxGraphImagesForNotifications
from ._graph_metric_expressions import (
    graph_metric_expression_registry,
    GraphMetricConstant,
    GraphMetricConstantNA,
    GraphMetricOperation,
    GraphMetricRRDSource,
)
from ._graph_specification import graph_specification_registry
from ._graph_templates import TemplateGraphSpecification
from ._html_render import AjaxGraphValuesAtTime, AjaxRenderGraph
from ._metric_backend_registry import (
    metric_backend_registry,
    MetricBackend,
)
from ._metric_visitor import MetricVisitor
from ._settings import ConfigVariableGraphTimeranges
from ._valuespecs import LivestatusQueryFunc, PageVsAutocomplete


def _register_graph_dispatchers(registry: GraphDispatcherRegistry, codec: GraphCodec) -> None:
    # Every graph kind of the edition is registered with that one codec.
    registry.register(template_graph_dispatcher(codec))


def register(
    edition: Edition,
    page_registry: PageRegistry,
    config_variable_registry: ConfigVariableRegistry,
    autocompleter_registry: AutocompleterRegistry,
    livestatus_query: LivestatusQueryFunc,
) -> None:
    page_registry.register(PageEndpoint("ajax_graph_values_at_time", AjaxGraphValuesAtTime()))
    page_registry.register(PageEndpoint("ajax_graph_images", AjaxGraphImagesForNotifications()))
    page_registry.register(PageEndpoint("ajax_render_graph", AjaxRenderGraph()))
    page_registry.register(PageEndpoint("ajax_vs_unit_resolver", PageVsAutocomplete()))

    config_variable_registry.register(ConfigVariableGraphTimeranges)

    def wrapped_autocompleter(
        config: object,
        value: str,
        params: dict,  # type: ignore[type-arg]
    ) -> Choices:
        return metrics_autocompleter(value, params, livestatus_query=livestatus_query)

    autocompleter_registry.register_autocompleter("monitored_metrics", wrapped_autocompleter)

    graph_metric_expression_registry.register(GraphMetricConstant)
    graph_metric_expression_registry.register(GraphMetricConstantNA)
    graph_metric_expression_registry.register(GraphMetricOperation)
    graph_metric_expression_registry.register(GraphMetricRRDSource)

    graph_specification_registry.register(ExplicitGraphSpecification)
    graph_specification_registry.register(TemplateGraphSpecification)

    _register_graph_dispatchers(graph_dispatcher_registry, community_graph_codec())

    metric_backend_registry.register(MetricBackend())

    register_visitor_class(MetricExtended, MetricVisitor)

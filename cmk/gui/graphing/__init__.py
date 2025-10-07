#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.version import Edition
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.valuespec import AutocompleterRegistry
from cmk.gui.watolib.config_domain_name import ConfigVariableRegistry

from ._autocompleter import metrics_autocompleter
from ._explicit_graphs import ExplicitGraphSpecification
from ._graph_metric_expressions import (
    graph_metric_expression_registry,
    GraphMetricConstant,
    GraphMetricConstantNA,
    GraphMetricOperation,
    GraphMetricRRDSource,
)
from ._graph_specification import graph_specification_registry
from ._graph_templates import TemplateGraphSpecification
from ._metric_backend_registry import (
    FetchTimeSeries,
    metric_backend_registry,
    MetricBackend,
)
from ._metrics import registered_metric_ids_and_titles
from ._perfometer import get_first_matching_perfometer
from ._settings import ConfigVariableGraphTimeranges
from ._valuespecs import PageVsAutocomplete


def register(
    edition: Edition,
    page_registry: PageRegistry,
    config_variable_registry: ConfigVariableRegistry,
    autocompleter_registry: AutocompleterRegistry,
) -> None:
    page_registry.register(PageEndpoint("ajax_vs_unit_resolver", PageVsAutocomplete))
    graph_metric_expression_registry.register(GraphMetricConstant)
    graph_metric_expression_registry.register(GraphMetricConstantNA)
    graph_metric_expression_registry.register(GraphMetricOperation)
    graph_metric_expression_registry.register(GraphMetricRRDSource)
    graph_specification_registry.register(ExplicitGraphSpecification)
    graph_specification_registry.register(TemplateGraphSpecification)
    config_variable_registry.register(ConfigVariableGraphTimeranges)
    autocompleter_registry.register_autocompleter("monitored_metrics", metrics_autocompleter)
    metric_backend_registry.register(
        MetricBackend(
            edition=edition,
            client=lambda *args, **kwargs: {},
        )
    )


__all__ = [
    "FetchTimeSeries",
    "metric_backend_registry",
    "get_first_matching_perfometer",
    "register",
    "registered_metric_ids_and_titles",
]

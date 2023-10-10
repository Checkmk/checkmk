#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.pages import PageRegistry
from cmk.gui.watolib.config_domain_name import ConfigVariableRegistry

from ._explicit_graphs import ExplicitGraphRecipeBuilder
from ._graph_recipe_builder import graph_recipe_builder_registry
from ._graph_templates import TemplateGraphRecipeBuilder
from ._perfometer import (
    get_first_matching_perfometer,
    LogarithmicPerfometerSpec,
    MetricometerRendererLogarithmic,
    parse_perfometers,
    perfometer_info,
    PerfometerSpec,
    renderer_registry,
)
from ._settings import ConfigVariableGraphTimeranges
from ._timeseries import register_time_series_expressions
from ._utils import time_series_expression_registry
from ._valuespecs import PageVsAutocomplete


def register(page_registry: PageRegistry, config_variable_registry: ConfigVariableRegistry) -> None:
    page_registry.register_page("ajax_vs_unit_resolver")(PageVsAutocomplete)
    graph_recipe_builder_registry.register(ExplicitGraphRecipeBuilder())
    graph_recipe_builder_registry.register(TemplateGraphRecipeBuilder())
    register_time_series_expressions(time_series_expression_registry)
    config_variable_registry.register(ConfigVariableGraphTimeranges)


__all__ = [
    "register",
    "get_first_matching_perfometer",
    "LogarithmicPerfometerSpec",
    "MetricometerRendererLogarithmic",
    "parse_perfometers",
    "perfometer_info",
    "PerfometerSpec",
    "renderer_registry",
]

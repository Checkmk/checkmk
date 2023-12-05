#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.pages import PageRegistry
from cmk.gui.watolib.config_domain_name import ConfigVariableRegistry

from . import _perfometer
from ._explicit_graphs import ExplicitGraphSpecification
from ._graph_specification import graph_specification_registry
from ._graph_templates import TemplateGraphSpecification
from ._perfometer import (
    get_first_matching_perfometer,
    LogarithmicPerfometerSpec,
    MetricometerRendererLegacyLogarithmic,
    parse_perfometers,
    perfometer_info,
    PerfometerSpec,
    renderer_registry,
)
from ._settings import ConfigVariableGraphTimeranges
from ._timeseries import register_time_series_expressions, time_series_expression_registry
from ._valuespecs import PageVsAutocomplete


def register(page_registry: PageRegistry, config_variable_registry: ConfigVariableRegistry) -> None:
    page_registry.register_page("ajax_vs_unit_resolver")(PageVsAutocomplete)
    graph_specification_registry.register(ExplicitGraphSpecification)
    graph_specification_registry.register(TemplateGraphSpecification)
    register_time_series_expressions(time_series_expression_registry)
    config_variable_registry.register(ConfigVariableGraphTimeranges)
    _perfometer.register()


__all__ = [
    "register",
    "get_first_matching_perfometer",
    "LogarithmicPerfometerSpec",
    "MetricometerRendererLegacyLogarithmic",
    "parse_perfometers",
    "perfometer_info",
    "PerfometerSpec",
    "renderer_registry",
]

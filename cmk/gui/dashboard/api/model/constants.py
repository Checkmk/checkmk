#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated, TypedDict

from annotated_types import Ge

from cmk.gui.dashboard.api.model.type_defs import AnnotatedInfoName
from cmk.gui.dashboard.api.model.widget import (
    WidgetRelativeGridPosition,
    WidgetRelativeGridSize,
    WidgetResponsiveGridSize,
)
from cmk.gui.dashboard.type_defs import ResponsiveGridBreakpoint
from cmk.gui.openapi.framework.model import api_field, api_model


class _BreakpointConfig(TypedDict):
    min_width: Annotated[int, Ge(0)]
    columns: Annotated[int, Ge(1)]


RESPONSIVE_GRID_BREAKPOINTS: dict[ResponsiveGridBreakpoint, _BreakpointConfig] = {
    "XS": {"min_width": 280, "columns": 4},
    "S": {"min_width": 535, "columns": 8},
    "M": {"min_width": 705, "columns": 12},
    "L": {"min_width": 961, "columns": 12},
    "XL": {"min_width": 1217, "columns": 24},
}


@api_model
class RelativeLayoutConstraintsModel:
    initial_size: WidgetRelativeGridSize = api_field(
        description="Initial size as (width, height) in relative grid units."
    )
    minimum_size: WidgetRelativeGridSize = api_field(
        description="Minimum size as (width, height) in relative grid units."
    )
    initial_position: WidgetRelativeGridPosition = api_field(
        description="Initial position as (x, y) in relative grid units."
    )
    is_resizable: bool = api_field(description="Whether the widget is resizable.")


@api_model
class ResponsiveLayoutBreakpointConstraintsModel:
    initial_size: WidgetResponsiveGridSize = api_field(
        description="Initial size when a widget is added to the dashboard."
    )
    minimum_size: WidgetResponsiveGridSize = api_field(
        description="Minimum size on this breakpoint."
    )


type ResponsiveLayoutConstraintsModel = dict[
    ResponsiveGridBreakpoint, ResponsiveLayoutBreakpointConstraintsModel
]


@api_model
class LayoutConstraintsModel:
    relative: RelativeLayoutConstraintsModel
    responsive: ResponsiveLayoutConstraintsModel


@api_model
class FilterContextConstants:
    restricted_to_single: list[AnnotatedInfoName] = api_field(
        description=(
            "A list of single infos that this widget content is restricted to. "
            "This means that the widget must be filtered to exactly one item for each info name."
        )
    )


@api_model
class WidgetConstraints:
    layout: LayoutConstraintsModel = api_field(description="Layout constraints for the widget.")
    filter_context: FilterContextConstants = api_field(
        description="Filter context constraints for the widget type."
    )
    title_macros: list[str] = api_field(description="Available macros for dynamic widget titles.")


@api_model
class ResponsiveGridBreakpointConfig:
    min_width: Annotated[int, Ge(0)] = api_field(
        description="Minimum width of the breakpoint in pixels."
    )
    columns: Annotated[int, Ge(0)] = api_field(
        description="Number of columns available at this breakpoint."
    )


@api_model
class DashboardConstantsResponse:
    widgets: dict[str, WidgetConstraints] = api_field(
        description="All widget types and their respective constraints"
    )
    responsive_grid_breakpoints: dict[ResponsiveGridBreakpoint, ResponsiveGridBreakpointConfig] = (
        api_field(
            description="The responsive grid breakpoint configuration.",
        )
    )

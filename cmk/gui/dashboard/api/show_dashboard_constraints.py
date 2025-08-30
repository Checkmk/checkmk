#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated, Literal

from annotated_types import Ge

from cmk.gui.dashboard.dashlet import dashlet_registry
from cmk.gui.dashboard.type_defs import ResponsiveGridBreakpoint
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import DomainObjectModel
from cmk.gui.openapi.restful_objects.constructors import object_href

from ._family import DASHBOARD_FAMILY
from ._utils import INTERNAL_TO_API_TYPE_NAME
from .model.constants import RESPONSIVE_GRID_BREAKPOINTS
from .model.type_defs import AnnotatedInfoName
from .model.widget import WidgetRelativeGridPosition, WidgetRelativeGridSize


@api_model
class RelativeLayoutConstraints:
    initial_size: WidgetRelativeGridSize = api_field(
        description="Initial size as (width, height) in relative grid units."
    )
    initial_position: WidgetRelativeGridPosition = api_field(
        description="Initial position as (x, y) in relative grid units."
    )
    is_resizable: bool = api_field(description="Whether the widget is resizable.")


@api_model
class LayoutConstraints:
    relative: RelativeLayoutConstraints


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
    layout: LayoutConstraints = api_field(description="Layout constraints for the widget.")
    filter_context: FilterContextConstants = api_field(
        description="Filter context constraints for the widget type."
    )


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


@api_model
class DashboardConstantsObject(DomainObjectModel):
    domainType: Literal["constant"] = api_field(description="The domain type of the object.")
    extensions: DashboardConstantsResponse = api_field(
        description="All the constants data of a dashboard."
    )


def show_dashboard_constants_v1() -> DashboardConstantsObject:
    """Show the dashboard constraints"""
    widgets_metadata = {}
    for widget_type, widget in dashlet_registry.items():
        if api_type_name := INTERNAL_TO_API_TYPE_NAME.get(widget_type):
            widgets_metadata[api_type_name] = WidgetConstraints(
                layout=LayoutConstraints(
                    relative=RelativeLayoutConstraints(
                        initial_size=WidgetRelativeGridSize.from_internal(widget.initial_size()),
                        initial_position=WidgetRelativeGridPosition.from_internal(
                            widget.initial_position()
                        ),
                        is_resizable=widget.is_resizable(),
                    )
                ),
                filter_context=FilterContextConstants(
                    restricted_to_single=list(widget.single_infos()),
                ),
            )

    return DashboardConstantsObject(
        domainType="constant",
        id="dashboard",
        title="Dashboard Constants",
        links=[],
        extensions=DashboardConstantsResponse(
            widgets=widgets_metadata,
            responsive_grid_breakpoints={
                breakpoint_id: ResponsiveGridBreakpointConfig(
                    min_width=config["min_width"], columns=config["columns"]
                )
                for breakpoint_id, config in RESPONSIVE_GRID_BREAKPOINTS.items()
            },
        ),
    )


ENDPOINT_SHOW_DASHBOARD_CONSTANTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("constant", "dashboard"),
        link_relation="cmk/fetch",
        method="get",
    ),
    permissions=EndpointPermissions(),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=show_dashboard_constants_v1)},
)

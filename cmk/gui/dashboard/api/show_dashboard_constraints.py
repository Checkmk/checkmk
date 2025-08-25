#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal

from cmk.gui.dashboard.dashlet import dashlet_registry
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
from ._model.widget import WidgetPosition, WidgetSize
from ._utils import INTERNAL_TO_API_TYPE_NAME


@api_model
class RelativeLayoutConstraints:
    initial_size: WidgetSize = api_field(
        description="Initial size as (width, height) in relative grid units."
    )
    initial_position: WidgetPosition = api_field(
        description="Initial position as (x, y) in relative grid units."
    )
    is_resizable: bool = api_field(description="Whether the widget is resizable.")


@api_model
class LayoutConstraints:
    relative: RelativeLayoutConstraints


@api_model
class WidgetConstraints:
    layout: LayoutConstraints = api_field(description="Layout constraints for the widget.")


@api_model
class DashboardConstraintsResponse:
    widgets: dict[str, WidgetConstraints] = api_field(
        description="All widget types and their respective constraints"
    )


@api_model
class DashboardConstraintsObject(DomainObjectModel):
    domainType: Literal["constant"] = api_field(description="The domain type of the object.")
    extensions: DashboardConstraintsResponse = api_field(
        description="All the constraints data of a dashboard."
    )


def show_dashboard_constraints_v1() -> DashboardConstraintsObject:
    """Show the dashboard constraints"""
    widgets_metadata = {}
    for widget_type, widget in dashlet_registry.items():
        if api_type_name := INTERNAL_TO_API_TYPE_NAME.get(widget_type):
            widgets_metadata[api_type_name] = WidgetConstraints(
                layout=LayoutConstraints(
                    relative=RelativeLayoutConstraints(
                        initial_size=WidgetSize.from_internal(widget.initial_size()),
                        initial_position=WidgetPosition.from_internal(widget.initial_position()),
                        is_resizable=widget.is_resizable(),
                    )
                )
            )

    return DashboardConstraintsObject(
        domainType="constant",
        id="dashboard",
        title="Dashboard Constants",
        links=[],
        extensions=DashboardConstraintsResponse(widgets=widgets_metadata),
    )


ENDPOINT_SHOW_DASHBOARD_CONSTANTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("constant", "dashboard"),
        link_relation="cmk/fetch",
        method="get",
    ),
    permissions=EndpointPermissions(),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=show_dashboard_constraints_v1)},
)

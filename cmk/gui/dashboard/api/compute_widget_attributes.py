#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href

from ._family import DASHBOARD_FAMILY
from ._utils import PERMISSIONS_DASHBOARD
from .model.type_defs import AnnotatedInfoName
from .model.widget import determine_widget_filter_used_infos
from .model.widget_content import WidgetContent


@api_model
class ComputedFilterContext:
    uses_infos: list[AnnotatedInfoName] = api_field(
        description=(
            "A list of info names that the widget content uses. "
            "This means that the widget can be filtered by these info names."
        )
    )


@api_model
class ComputedWidgetSpec:
    filter_context: ComputedFilterContext = api_field(
        description="Computed filter context attributes for the widget."
    )


@api_model
class ComputedWidgetSpecResponse:
    domainType: Literal["widget-compute"] = api_field(description="The domain type of the object.")
    value: ComputedWidgetSpec = api_field(description="Computed widget specification attributes")


@api_model
class ComputedWidgetSpecRequest:
    content: WidgetContent = api_field(description="Widget content to compute attributes for.")


def compute_widget_attributes_v1(body: ComputedWidgetSpecRequest) -> ComputedWidgetSpecResponse:
    """Compute widget specification attributes"""
    user.need_permission("general.edit_dashboards")
    widget_config = body.content.to_internal()
    return ComputedWidgetSpecResponse(
        domainType="widget-compute",
        value=ComputedWidgetSpec(
            filter_context=ComputedFilterContext(
                uses_infos=determine_widget_filter_used_infos(widget_config)
            )
        ),
    )


ENDPOINT_COMPUTE_WIDGET_ATTRIBUTES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href(domain_type="dashboard", action="compute-widget-attributes"),
        link_relation="cmk/compute",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_DASHBOARD),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=compute_widget_attributes_v1)},
)

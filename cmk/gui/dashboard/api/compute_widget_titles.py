#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal

from cmk.gui.dashboard.dashlet.registry import dashlet_registry
from cmk.gui.dashboard.type_defs import DashletConfig
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
from cmk.gui.openapi.framework.model.base_models import DomainObjectModel
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href

from ._family import DASHBOARD_FAMILY
from ._utils import PERMISSIONS_DASHBOARD
from .model.widget import BaseWidgetRequest


@api_model
class ComputeWidgetTitleWidgetRequest(BaseWidgetRequest):
    def to_internal(self) -> DashletConfig:
        return self._to_internal_without_layout()


@api_model
class ComputeWidgetTitlesRequest:
    widgets: dict[str, ComputeWidgetTitleWidgetRequest] = api_field(
        description="All widgets to compute titles for."
    )


@api_model
class ComputeWidgetTitlesExtensions:
    titles: dict[str, str] = api_field(description="Computed widget titles by widget ID.")


@api_model
class ComputeWidgetTitlesResponse(DomainObjectModel):
    domainType: Literal["dashboard-widget-titles"] = api_field(  # type: ignore[mutable-override]
        description="The domain type of the object."
    )
    extensions: ComputeWidgetTitlesExtensions = api_field(
        description="Extensions for the response."
    )


def _compute_title(widget_request: ComputeWidgetTitleWidgetRequest) -> str:
    widget_config = widget_request.to_internal()
    widget_type = dashlet_registry[widget_config["type"]]
    widget = widget_type(widget_config)
    return widget.compute_title()


def compute_widget_titles_v1(body: ComputeWidgetTitlesRequest) -> ComputeWidgetTitlesResponse:
    """Compute multiple widget titles."""
    user.need_permission("general.edit_dashboards")
    return ComputeWidgetTitlesResponse(
        domainType="dashboard-widget-titles",
        extensions=ComputeWidgetTitlesExtensions(
            titles={
                widget_id: _compute_title(widget_request)
                for widget_id, widget_request in body.widgets.items()
            }
        ),
        links=[],
    )


ENDPOINT_COMPUTE_WIDGET_TITLES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href(domain_type="dashboard", action="compute-widget-titles"),
        link_relation="cmk/compute_dashboard_widget_titles",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_DASHBOARD),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=compute_widget_titles_v1)},
)

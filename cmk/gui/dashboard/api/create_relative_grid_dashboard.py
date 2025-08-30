#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from livestatus import SiteConfigurations

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.response import ApiResponse, TypedResponse
from cmk.gui.openapi.restful_objects.constructors import collection_href

from .. import DashboardConfig
from ..store import DashboardStore, save_all_dashboards
from ._family import DASHBOARD_FAMILY
from ._utils import PERMISSIONS_DASHBOARD, serialize_relative_grid_dashboard, sync_user_to_remotes
from .model.dashboard import BaseRelativeGridDashboardRequest, RelativeGridDashboardResponse
from .model.response_model import RelativeGridDashboardDomainObject


@api_model
class CreateDashboardV1(BaseRelativeGridDashboardRequest):
    dashboard_id: str = api_field(
        serialization_alias="id",
        description="Unique identifier for the dashboard.",
        example="custom_dashboard",
        pattern=r"^[a-zA-Z0-9_]+$",
    )


def _save_dashboard_to_file(sites: SiteConfigurations, dashboard: DashboardConfig) -> None:
    dashboard_id = dashboard["name"]
    store = DashboardStore.get_instance()
    store.all[(user.id, dashboard_id)] = dashboard

    save_all_dashboards()
    sync_user_to_remotes(sites)


def create_relative_grid_dashboard_v1(
    api_context: ApiContext, body: CreateDashboardV1
) -> TypedResponse[RelativeGridDashboardDomainObject]:
    """Create a dashboard."""
    body.validate(api_context)
    user.need_permission("general.edit_dashboards")

    internal = body.to_internal(user.ident, body.dashboard_id)
    _save_dashboard_to_file(api_context.config.sites, internal)

    return ApiResponse(
        serialize_relative_grid_dashboard(
            body.dashboard_id, RelativeGridDashboardResponse.from_internal(internal)
        ),
        status_code=201,
    )


ENDPOINT_CREATE_RELATIVE_GRID_DASHBOARD = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("dashboard_relative_grid"),
        link_relation="cmk/create",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_DASHBOARD),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=create_relative_grid_dashboard_v1)},
)

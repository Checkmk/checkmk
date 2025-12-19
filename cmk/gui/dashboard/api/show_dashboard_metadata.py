#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.restful_objects.constructors import object_href

from ..metadata import DashboardMetadataObject
from ._family import DASHBOARD_FAMILY
from ._utils import (
    dashboard_owner_description,
    DashboardOwnerWithBuiltin,
    get_dashboard_for_read,
    PERMISSIONS_DASHBOARD,
)
from .model.metadata import DashboardMetadata, DashboardMetadataModel


def show_dashboard_metadata_v1(
    api_context: ApiContext,
    dashboard_id: Annotated[
        str,
        PathParam(description="Dashboard ID", example="main"),
    ],
    owner: Annotated[
        DashboardOwnerWithBuiltin,
        QueryParam(
            description=dashboard_owner_description("The owner of the dashboard."),
            example="admin",
        ),
    ] = ApiOmitted(),
) -> DashboardMetadataModel:
    """Show a dashboard's metadata."""
    dashboard = get_dashboard_for_read(owner, dashboard_id)
    user_permissions = api_context.config.user_permissions()
    return DashboardMetadataModel(
        id=dashboard_id,
        domainType="dashboard_metadata",
        extensions=DashboardMetadata.from_dashboard_metadata_object(
            DashboardMetadataObject.from_dashboard_config(dashboard, user_permissions)
        ),
        links=[],
    )


ENDPOINT_SHOW_DASHBOARD_METADATA = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("dashboard_metadata", "{dashboard_id}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_DASHBOARD),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=show_dashboard_metadata_v1)},
)

#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from cmk.ccc.user import UserId
from cmk.gui.dashboard.store import get_permitted_dashboards, get_permitted_dashboards_by_owners
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
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.type_defs import AnnotatedUserId

from ..metadata import DashboardMetadataObject
from ._family import DASHBOARD_FAMILY
from ._utils import PERMISSIONS_DASHBOARD
from .model.metadata import DashboardMetadata, DashboardMetadataModel


def show_dashboard_metadata_v1(
    api_context: ApiContext,
    dashboard_id: Annotated[
        str,
        PathParam(description="Dashboard ID", example="main"),
    ],
    owner: Annotated[
        Literal[""] | AnnotatedUserId | ApiOmitted,
        QueryParam(
            description="The owner of the dashboard. If not provided, the current user is assumed. Use an empty string to indicate a built-in dashboard.",
            example="admin",
        ),
    ] = ApiOmitted(),
) -> DashboardMetadataModel:
    """Show a dashboard's metadata."""

    if isinstance(owner, ApiOmitted):
        dashboards = get_permitted_dashboards()
        dashboard = dashboards.get(dashboard_id)
    else:
        user_id = UserId.builtin() if owner == "" else owner
        dashboards_by_owners = get_permitted_dashboards_by_owners()
        if dashboard_id not in dashboards_by_owners:
            raise ProblemException(
                status=404,
                title="Dashboard not found",
                detail=f"The dashboard with ID '{dashboard_id}' does not exist or you do not have permission to view it.",
            )

        owner_dashboards = dashboards_by_owners[dashboard_id]
        dashboard = owner_dashboards.get(user_id)

    if dashboard is None:
        raise ProblemException(
            status=404,
            title="Dashboard not found",
            detail=f"The dashboard with ID '{dashboard_id}' does not exist{'' if isinstance(owner, ApiOmitted) else 'for the specified owner'} or you do not have permission to view it.",
        )

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

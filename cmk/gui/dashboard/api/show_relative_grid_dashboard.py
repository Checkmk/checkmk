#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from cmk.gui.openapi.framework import (
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

from ..metadata import dashboard_uses_relative_grid
from ._family import DASHBOARD_FAMILY
from ._utils import (
    dashboard_owner_description,
    DashboardOwnerWithBuiltin,
    get_dashboard_for_read,
    PERMISSIONS_DASHBOARD,
    serialize_relative_grid_dashboard,
)
from .model.dashboard import RelativeGridDashboardResponse
from .model.response_model import RelativeGridDashboardDomainObject


def show_relative_grid_dashboard_v1(
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
) -> RelativeGridDashboardDomainObject:
    """Show a dashboard."""
    dashboard = get_dashboard_for_read(owner, dashboard_id)
    if not dashboard_uses_relative_grid(dashboard):
        raise ProblemException(
            status=400,
            title="Invalid dashboard layout",
            detail=f"The dashboard with ID '{dashboard_id}' is not a relative grid dashboard.",
        )
    return serialize_relative_grid_dashboard(
        dashboard_id, RelativeGridDashboardResponse.from_internal(dashboard)
    )


ENDPOINT_SHOW_RELATIVE_GRID_DASHBOARD = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("dashboard_relative_grid", "{dashboard_id}"),
        link_relation="cmk/show_dashboard_relative_grid",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_DASHBOARD),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=show_relative_grid_dashboard_v1)},
)

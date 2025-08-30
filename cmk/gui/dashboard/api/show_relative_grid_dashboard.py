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
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import ProblemException

from ..store import get_permitted_dashboards
from ._family import DASHBOARD_FAMILY
from ._utils import (
    dashboard_uses_relative_grid,
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
) -> RelativeGridDashboardDomainObject:
    """Show a dashboard."""
    dashboards = get_permitted_dashboards()
    if dashboard_id not in dashboards:
        raise ProblemException(
            status=404,
            title="Dashboard not found",
            detail=f"The dashboard with ID '{dashboard_id}' does not exist or you do not have permission to view it.",
        )
    dashboard = dashboards[dashboard_id]
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
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_DASHBOARD),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=show_relative_grid_dashboard_v1)},
)

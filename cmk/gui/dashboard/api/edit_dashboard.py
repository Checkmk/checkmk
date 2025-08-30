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
from cmk.gui.openapi.framework.model import api_model, ApiOmitted
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.type_defs import AnnotatedUserId

from ..store import get_all_dashboards, save_all_dashboards
from ._family import DASHBOARD_FAMILY
from ._utils import (
    get_permitted_user_id,
    PERMISSIONS_DASHBOARD,
    serialize_dashboard,
    sync_user_to_remotes,
)
from .model.dashboard import BaseDashboardRequest, DashboardResponse
from .model.response_model import DashboardDomainObject


@api_model
class EditDashboardV1(BaseDashboardRequest):
    pass


def edit_dashboard_v1(
    api_context: ApiContext,
    body: EditDashboardV1,
    dashboard_id: Annotated[
        str,
        PathParam(description="Dashboard ID", example="main"),
    ],
    owner: Annotated[
        AnnotatedUserId | ApiOmitted,
        QueryParam(
            description="The owner of the dashboard. If not provided, the current user is assumed.",
            example="admin",
        ),
    ] = ApiOmitted(),
) -> DashboardDomainObject:
    """Edit a dashboard."""
    body.validate(api_context)
    user_id = get_permitted_user_id(owner, action="edit")

    key = (user_id, dashboard_id)
    dashboards = get_all_dashboards()
    if key not in dashboards:
        raise ProblemException(
            status=404,
            title="Dashboard not found",
            detail=f"The dashboard with ID '{dashboard_id}' does not exist for user '{user_id}'.",
        )
    dashboards[key] = body.to_internal(user_id, dashboard_id)
    save_all_dashboards()
    sync_user_to_remotes(api_context.config.sites)
    return serialize_dashboard(dashboard_id, DashboardResponse.from_internal(dashboards[key]))


ENDPOINT_EDIT_DASHBOARD = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("dashboard", "{dashboard_id}"),
        link_relation=".../update",
        method="put",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_DASHBOARD),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=edit_dashboard_v1)},
)

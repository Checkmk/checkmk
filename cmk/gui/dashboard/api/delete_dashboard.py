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
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.type_defs import AnnotatedUserId

from ..store import get_all_dashboards, save_all_dashboards
from ._family import DASHBOARD_FAMILY
from ._utils import get_permitted_user_id, PERMISSIONS_DASHBOARD, sync_user_to_remotes


def delete_dashboard_v1(
    api_context: ApiContext,
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
) -> None:
    """Delete a dashboard."""
    user_id = get_permitted_user_id(owner, action="delete")

    key = (user_id, dashboard_id)
    dashboards = get_all_dashboards()
    if key not in dashboards:
        raise ProblemException(
            status=404,
            title="Dashboard not found",
            detail=f"The dashboard with ID '{dashboard_id}' does not exist for user '{user_id}'.",
        )
    del dashboards[key]
    save_all_dashboards()
    sync_user_to_remotes(api_context.config.sites)


ENDPOINT_DELETE_DASHBOARD = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("dashboard", "{dashboard_id}"),
        link_relation=".../delete",
        method="delete",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_DASHBOARD),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=delete_dashboard_v1)},
)

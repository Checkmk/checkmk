#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.utils import ProblemException

from ...openapi.framework.model.response import ApiResponse
from .. import get_all_dashboards
from ..metadata import dashboard_uses_relative_grid
from ._family import DASHBOARD_FAMILY
from ._utils import (
    clone_dashboard_config,
    dashboard_owner_description,
    DashboardOwnerWithBuiltin,
    get_dashboard_for_read,
    make_pending_changes,
    PERMISSIONS_DASHBOARD,
    save_dashboard_to_file,
    serialize_relative_grid_dashboard,
)
from .model.dashboard import DashboardGeneralSettings, RelativeGridDashboardResponse
from .model.response_model import RelativeGridDashboardDomainObject


@api_model
class CloneDashboardV1:
    reference_dashboard_id: str = api_field(
        description="The ID of the dashboard to clone.",
        example="existing_dashboard",
    )
    reference_dashboard_owner: DashboardOwnerWithBuiltin = api_field(
        description=dashboard_owner_description("The owner of the dashboard to clone."),
        example="admin",
        default_factory=ApiOmitted,
    )
    dashboard_id: str = api_field(
        description="Unique identifier for the dashboard.",
        example="custom_dashboard",
        pattern=r"^[a-zA-Z0-9_]+$",
    )
    general_settings: DashboardGeneralSettings | ApiOmitted = api_field(
        description="General settings for the cloned dashboard.",
        default_factory=ApiOmitted,
    )


def clone_as_relative_grid_dashboard_v1(
    api_context: ApiContext,
    body: CloneDashboardV1,
) -> ApiResponse[RelativeGridDashboardDomainObject]:
    """Clone as relative dashboard"""
    user.need_permission("general.edit_dashboards")
    dashboard_to_clone = get_dashboard_for_read(
        body.reference_dashboard_owner, body.reference_dashboard_id
    )
    owner = user.ident

    if (owner, body.dashboard_id) in get_all_dashboards():
        raise ProblemException(
            status=400,
            title="Dashboard ID already exists",
            detail=f"A dashboard with ID '{body.dashboard_id}' already exists for you.",
        )

    if not dashboard_uses_relative_grid(dashboard_to_clone):
        raise ProblemException(
            status=400,
            title="Invalid dashboard layout",
            detail=f"The dashboard with ID '{body.reference_dashboard_id}' is not a relative grid dashboard.",
        )

    cloned_dashboard = clone_dashboard_config(
        dashboard_to_clone, owner, body.dashboard_id, body.general_settings
    )

    save_dashboard_to_file(
        api_context.config.sites,
        cloned_dashboard,
        owner,
        pending_changes=make_pending_changes(api_context),
    )

    return ApiResponse(
        serialize_relative_grid_dashboard(
            body.dashboard_id, RelativeGridDashboardResponse.from_internal(cloned_dashboard)
        ),
        status_code=201,
    )


ENDPOINT_CLONE_AS_RELATIVE_GRID_DASHBOARD = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("dashboard_relative_grid", "clone"),
        link_relation="cmk/clone_dashboard_relative_grid",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_DASHBOARD),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=clone_as_relative_grid_dashboard_v1)},
)

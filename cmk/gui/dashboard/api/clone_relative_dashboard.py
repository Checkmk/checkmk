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
from .. import DashboardConfig, get_all_dashboards
from ..metadata import dashboard_uses_relative_grid
from ._family import DASHBOARD_FAMILY
from ._utils import (
    dashboard_owner_description,
    DashboardOwnerWithBuiltin,
    get_dashboard_for_read,
    PERMISSIONS_DASHBOARD,
    save_dashboard_to_file,
    serialize_relative_grid_dashboard,
)
from .model.dashboard import DashboardGeneralSettings, DashboardIcon, RelativeGridDashboardResponse
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

    general_settings = body.general_settings
    if not isinstance(general_settings, ApiOmitted):
        description = (
            ""
            if isinstance(general_settings.description, ApiOmitted)
            else general_settings.description
        )
        cloned_dashboard: DashboardConfig = {
            **dashboard_to_clone,
            "owner": owner,
            "name": body.dashboard_id,
            "packaged": False,
            "add_context_to_title": general_settings.title.include_context,
            "title": general_settings.title.text,
            "description": description,
            "topic": general_settings.menu.topic,
            "sort_index": general_settings.menu.sort_index,
            "is_show_more": general_settings.menu.is_show_more,
            "icon": DashboardIcon.to_internal(general_settings.menu.icon),
            "hidden": general_settings.visibility.hide_in_monitor_menu,
            "hidebutton": general_settings.visibility.hide_in_drop_down_menus,
            "public": general_settings.visibility.share_to_internal(),
            "main_menu_search_terms": general_settings.menu.search_terms,
            "show_title": general_settings.title.render,
        }
    else:
        cloned_dashboard = {
            **dashboard_to_clone,
            "owner": owner,
            "name": body.dashboard_id,
            "packaged": False,
        }

    if cloned_dashboard.get("public_token_id"):
        cloned_dashboard["public_token_id"] = None  # Remove token reference in cloned dashboard

    save_dashboard_to_file(api_context.config.sites, cloned_dashboard, owner)

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

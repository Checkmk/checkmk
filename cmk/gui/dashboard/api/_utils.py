#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from concurrent.futures.thread import ThreadPoolExecutor
from http import HTTPStatus
from typing import Any, Literal

from livestatus import SiteConfigurations

import cmk.gui.utils.permission_verification as permissions
from cmk.ccc.user import UserId
from cmk.gui.dashboard.dashlet import dashlet_registry
from cmk.gui.dashboard.type_defs import DashboardConfig
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.openapi.framework.utils import dump_dict_without_omitted
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.type_defs import AnnotatedUserId, VisualTypeName
from cmk.gui.user_async_replication import add_profile_replication_change
from cmk.gui.userdb import load_user
from cmk.gui.visuals._store import load_raw_visuals_of_a_user
from cmk.gui.watolib.automations import (
    remote_automation_config_from_site_config,
)
from cmk.gui.watolib.user_profile import push_user_profiles_to_site_transitional_wrapper
from cmk.gui.watolib.users import get_enabled_remote_sites_for_user
from cmk.utils.automation_config import RemoteAutomationConfig

from ..dashlet.base import ResponsiveLayoutBreakpointConstraints
from ..store import (
    DashboardStore,
    get_all_dashboards,
    get_permitted_dashboards,
    get_permitted_dashboards_by_owners,
    save_all_dashboards,
)
from ..title_macros import get_title_macros
from .model.constants import (
    DashboardConstantsResponse,
    FilterContextConstants,
    LayoutConstraintsModel,
    RelativeLayoutConstraintsModel,
    RESPONSIVE_GRID_BREAKPOINTS,
    ResponsiveGridBreakpointConfig,
    ResponsiveLayoutBreakpointConstraintsModel,
    WidgetConstraints,
)
from .model.dashboard import RelativeGridDashboardResponse
from .model.response_model import RelativeGridDashboardDomainObject
from .model.widget import (
    WidgetRelativeGridPosition,
    WidgetRelativeGridSize,
    WidgetResponsiveGridSize,
)

INTERNAL_TO_API_TYPE_NAME: Mapping[str, str] = {
    "problem_graph": "problem_graph",
    "combined_graph": "combined_graph",
    "single_timeseries": "single_timeseries",
    "custom_graph": "custom_graph",
    "pnpgraph": "performance_graph",
    "inventory": "inventory",
    "barplot": "barplot",
    "gauge": "gauge",
    "single_metric": "single_metric",
    "average_scatterplot": "average_scatterplot",
    "top_list": "top_list",
    "ntop_alerts": "ntop_alerts",
    "ntop_flows": "ntop_flows",
    "ntop_top_talkers": "ntop_top_talkers",
    "alert_overview": "alert_overview",
    "site_overview": "site_overview",
    "snapin": "sidebar_element",
    "state_host": "host_state",
    "state_service": "service_state",
    "host_state_summary": "host_state_summary",
    "service_state_summary": "service_state_summary",
    "hoststats": "host_stats",
    "servicestats": "service_stats",
    "eventstats": "event_stats",
    "nodata": "static_text",
    "alerts_bar_chart": "alert_timeline",
    "notifications_bar_chart": "notification_timeline",
    "url": "url",
    "user_messages": "user_messages",
    "linked_view": "linked_view",
    "embedded_view": "embedded_view",
}

_PERMISSIONS_MISC = permissions.Optional(
    permissions.AllPerm(
        [
            permissions.Perm("general.see_all"),
            permissions.Perm("bi.see_all"),
            permissions.Perm("mkeventd.seeall"),
        ]
    )
)

_PERMISSIONS_PAGE_TOPICS = permissions.Optional(
    permissions.AllPerm(
        [
            permissions.Perm("general.see_user_pagetype_topic"),
            permissions.PrefixPerm("pagetype_topic"),
        ]
    )
)

# if a dashboard contains view widgets, these might come up (even for reads)
_PERMISSIONS_VIEW_WIDGET = permissions.Optional(
    permissions.AllPerm(
        [
            permissions.Perm("general.edit_views"),  # always required, even for reads
            # optional permissions to allow access to more views the user doesn't own
            permissions.Perm("general.see_user_views"),
            permissions.Perm("general.see_packaged_views"),
            # every view has its own permissions, all of which might be checked (and are optional)
            permissions.PrefixPerm("view"),
        ]
    )
)

# if a dashboard contains graphs, these might come up (even for reads)
_PERMISSIONS_GRAPH_WIDGET = permissions.Optional(
    permissions.AllPerm(
        [
            permissions.OkayToIgnorePerm("general.edit_custom_graph"),  # yes, even for reads
            permissions.OkayToIgnorePerm("general.see_user_custom_graph"),
            permissions.OkayToIgnorePerm("general.see_user_graph_tuning"),
        ]
    )
)

PERMISSIONS_DASHBOARD = permissions.AllPerm(
    [
        permissions.Perm("general.edit_dashboards"),  # always required, even for reads
        # these 4 are optional, allowing access to more dashboards the user doesn't own
        permissions.Optional(permissions.Perm("general.force_dashboards")),
        permissions.Optional(permissions.Perm("general.see_user_dashboards")),
        permissions.Optional(permissions.Perm("general.see_packaged_dashboards")),
        permissions.Optional(permissions.Perm("general.edit_foreign_dashboards")),
        # breadcrumb metadata optional, required for every dashboard
        _PERMISSIONS_PAGE_TOPICS,
        # every dashboard has its own permissions, all of which might be checked (and are optional)
        permissions.PrefixPerm("dashboard"),
        # dashboards which contain certain widgets need extra permissions to view/modify them
        _PERMISSIONS_VIEW_WIDGET,
        _PERMISSIONS_GRAPH_WIDGET,
        # somewhere these are also checked
        _PERMISSIONS_MISC,
    ]
)
PERMISSIONS_DASHBOARD_EDIT = permissions.AllPerm(
    [
        *PERMISSIONS_DASHBOARD.perms,
        # extra permissions required for editing foreign dashboards
        permissions.Optional(permissions.Perm("general.edit_foreign_dashboards")),
    ]
)

type DashboardOwnerWithBuiltin = Literal[""] | AnnotatedUserId | ApiOmitted


def dashboard_owner_description(description: str) -> str:
    return (
        f"{description} Use an empty string for built-in dashboards. If not provided, the best "
        "matching dashboard for the current user is assumed."
    )


def get_permitted_user_id(owner: UserId | ApiOmitted, action: Literal["delete", "edit"]) -> UserId:
    """Get the user ID from the owner field, defaulting to the current user.

    Validates that the user has permission to perform the action on foreign dashboards.
    And that the built-in user was not chosen.
    """
    user.need_permission("general.edit_dashboards")
    user_id = user.ident
    if isinstance(owner, ApiOmitted) or owner == user_id:
        return user_id

    if owner == UserId.builtin():
        raise ProblemException(
            status=HTTPStatus.FORBIDDEN,
            title="Forbidden",
            detail=f"You are not allowed to {action} dashboards owned by the built-in user.",
        )

    user.need_permission(f"general.{action}_foreign_dashboards")
    return owner


def get_dashboard_for_edit(owner: UserId | ApiOmitted, dashboard_id: str) -> DashboardConfig:
    """Load a dashboard for editing, verifying permissions."""
    dashboard_owner = get_permitted_user_id(owner, action="edit")

    key = (dashboard_owner, dashboard_id)
    dashboards = get_all_dashboards()
    if key not in dashboards:
        raise ProblemException(
            status=404,
            title="Dashboard not found",
            detail=f"The dashboard with ID '{dashboard_id}' does not exist for user '{dashboard_owner}'.",
        )
    return dashboards[key]


def get_dashboard_for_read(owner: DashboardOwnerWithBuiltin, dashboard_id: str) -> DashboardConfig:
    """Load a dashboard for reading, verifying permissions."""
    if isinstance(owner, ApiOmitted):
        dashboards = get_permitted_dashboards()
        dashboard = dashboards.get(dashboard_id)
        owner_msg = ""
    else:
        user_id = UserId.builtin() if owner == "" else owner
        dashboards_by_owners = get_permitted_dashboards_by_owners()
        dashboard = dashboards_by_owners.get(dashboard_id, {}).get(user_id)
        owner_msg = " for the specified owner"

    if dashboard is None:
        raise ProblemException(
            status=404,
            title="Dashboard not found",
            detail=f"The dashboard with ID '{dashboard_id}' does not exist{owner_msg} or you do not have permission to view it.",
        )
    return dashboard


def serialize_relative_grid_dashboard(
    dashboard_id: str, dashboard: RelativeGridDashboardResponse
) -> RelativeGridDashboardDomainObject:
    return RelativeGridDashboardDomainObject(
        domainType="dashboard",
        id=dashboard_id,
        title=dashboard.general_settings.title.text,
        links=generate_links("dashboard", dashboard_id),
        extensions=dashboard,
    )


def save_dashboard_to_file(
    sites: SiteConfigurations,
    dashboard: DashboardConfig,
    user_id: UserId,
    old_dashboard_id: str | None = None,
) -> None:
    dashboard_id = dashboard["name"]
    store = DashboardStore.get_instance()
    # TODO: tests, update spec & frontend
    if old_dashboard_id and old_dashboard_id != dashboard_id:
        if (user_id, dashboard_id) in store.all:
            raise ProblemException(
                status=400,
                title="Dashboard ID already in use",
                detail=f"A dashboard with ID '{dashboard_id}' already exists for user '{user_id}'.",
            )
        store.all.pop((user_id, old_dashboard_id), None)
    store.all[(user_id, dashboard_id)] = dashboard

    save_all_dashboards(user_id)
    sync_user_to_remotes(sites, user_id)


def sync_user_to_remotes(sites: SiteConfigurations, user_id: UserId) -> None:
    """Synchronize the user profile and their dashboards to all enabled remote sites.

    This does not sync other visuals."""
    if user_id == user.id:
        user_spec = user.attributes
    else:
        user_spec = load_user(user_id)

    user_remote_sites = get_enabled_remote_sites_for_user(user_spec, sites)
    if not user_remote_sites:
        return

    remote_configs = []
    for site_id, site in user_remote_sites.items():
        if "secret" not in site:
            add_profile_replication_change(site_id, "Not logged in.")
            continue

        remote_configs.append(remote_automation_config_from_site_config(site))

    if not remote_configs:
        return

    dashboards = load_raw_visuals_of_a_user("dashboards", user_id)
    visuals: Mapping[UserId, Mapping[VisualTypeName, Mapping[str, Any]]] = {
        user_id: {"dashboards": dashboards}
    }

    def push(automation_config: RemoteAutomationConfig) -> None:
        push_user_profiles_to_site_transitional_wrapper(
            automation_config=automation_config,
            user_profiles={user_id: user_spec},
            visuals=visuals,
            debug=False,
        )

    with ThreadPoolExecutor(max_workers=len(remote_configs)) as executor:
        executor.map(push, remote_configs)


def convert_internal_relative_dashboard_to_api_model_dict(
    dashboard_config: DashboardConfig,
) -> dict[str, object]:
    dashboard_relative_grid = RelativeGridDashboardResponse.from_internal(dashboard_config)
    return dump_dict_without_omitted(RelativeGridDashboardResponse, dashboard_relative_grid)


class DashboardConstants:
    @staticmethod
    def _responsive_breakpoint_from_internal(
        internal: ResponsiveLayoutBreakpointConstraints,
    ) -> ResponsiveLayoutBreakpointConstraintsModel:
        return ResponsiveLayoutBreakpointConstraintsModel(
            initial_size=WidgetResponsiveGridSize(
                columns=internal.initial_size.width, rows=internal.initial_size.height
            ),
            minimum_size=WidgetResponsiveGridSize(
                columns=internal.minimum_size.width, rows=internal.minimum_size.height
            ),
        )

    @staticmethod
    def generate_api_response() -> DashboardConstantsResponse:
        widgets_metadata = {}
        for widget_type, widget in dashlet_registry.items():
            if api_type_name := INTERNAL_TO_API_TYPE_NAME.get(widget_type):
                relative_constraints = widget.relative_layout_constraints()
                responsive_constraints = widget.responsive_layout_constraints()
                title_macros = get_title_macros(
                    widget.single_infos(), widget.get_additional_macro_names()
                )
                widgets_metadata[api_type_name] = WidgetConstraints(
                    layout=LayoutConstraintsModel(
                        relative=RelativeLayoutConstraintsModel(
                            initial_size=WidgetRelativeGridSize(
                                width=relative_constraints.initial_size.width,
                                height=relative_constraints.initial_size.height,
                            ),
                            minimum_size=WidgetRelativeGridSize(
                                width=relative_constraints.minimum_size.width,
                                height=relative_constraints.minimum_size.height,
                            ),
                            initial_position=WidgetRelativeGridPosition(
                                x=relative_constraints.initial_position.x,
                                y=relative_constraints.initial_position.y,
                            ),
                            is_resizable=relative_constraints.is_resizable,
                        ),
                        responsive={
                            "XS": DashboardConstants._responsive_breakpoint_from_internal(
                                responsive_constraints.XS
                            ),
                            "S": DashboardConstants._responsive_breakpoint_from_internal(
                                responsive_constraints.S
                            ),
                            "M": DashboardConstants._responsive_breakpoint_from_internal(
                                responsive_constraints.M
                            ),
                            "L": DashboardConstants._responsive_breakpoint_from_internal(
                                responsive_constraints.L
                            ),
                            "XL": DashboardConstants._responsive_breakpoint_from_internal(
                                responsive_constraints.XL
                            ),
                        },
                    ),
                    filter_context=FilterContextConstants(
                        restricted_to_single=list(widget.single_infos()),
                    ),
                    title_macros=title_macros,
                )

        return DashboardConstantsResponse(
            widgets=widgets_metadata,
            responsive_grid_breakpoints={
                breakpoint_id: ResponsiveGridBreakpointConfig(
                    min_width=config["min_width"], columns=config["columns"]
                )
                for breakpoint_id, config in RESPONSIVE_GRID_BREAKPOINTS.items()
            },
        )

    @staticmethod
    def dict_output() -> dict[str, object]:
        response = DashboardConstants.generate_api_response()
        return dump_dict_without_omitted(DashboardConstantsResponse, response)

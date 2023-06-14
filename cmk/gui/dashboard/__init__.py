#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.version as cmk_version

import cmk.gui.utils as utils
import cmk.gui.visuals as visuals
from cmk.gui.config import default_authorized_builtin_role_ids
from cmk.gui.i18n import _
from cmk.gui.pages import PageRegistry
from cmk.gui.permissions import (
    declare_dynamic_permissions,
    declare_permission,
    permission_registry,
    PermissionSection,
    PermissionSectionRegistry,
)
from cmk.gui.plugins.visuals.utils import VisualTypeRegistry

from .builtin_dashboards import builtin_dashboards, GROW, MAX
from .cre_dashboards import register_builtin_dashboards
from .dashlet import (
    ABCFigureDashlet,
    Dashlet,
    dashlet_registry,
    DashletConfig,
    DashletRegistry,
    FigureDashletPage,
    IFrameDashlet,
    LinkedViewDashletConfig,
    register_dashlets,
    StaticTextDashletConfig,
    ViewDashletConfig,
)
from .page_create_dashboard import page_create_dashboard
from .page_create_view_dashlet import (
    page_create_link_view_dashlet,
    page_create_view_dashlet,
    page_create_view_dashlet_infos,
)
from .page_edit_dashboard import page_edit_dashboard
from .page_edit_dashboard_actions import ajax_dashlet_pos, page_clone_dashlet, page_delete_dashlet
from .page_edit_dashboards import page_edit_dashboards
from .page_edit_dashlet import EditDashletPage
from .page_show_dashboard import (
    ajax_dashlet,
    AjaxInitialDashboardFilters,
    get_topology_context_and_filters,
    page_dashboard,
)
from .store import get_all_dashboards, get_dashlet, get_permitted_dashboards
from .title_macros import render_title_with_macros_string
from .type_defs import DashboardConfig
from .visual_type import VisualTypeDashboards

__all__ = [
    "register",
    "load_plugins",
    "DashletConfig",
    "DashboardConfig",
    "builtin_dashboards",
    "MAX",
    "GROW",
    "dashlet_registry",
    "LinkedViewDashletConfig",
    "ViewDashletConfig",
    "StaticTextDashletConfig",
    "get_dashlet",
    "get_topology_context_and_filters",
    "get_all_dashboards",
    "get_permitted_dashboards",
    "render_title_with_macros_string",
    "ABCFigureDashlet",
]


def register(
    permission_section_registry: PermissionSectionRegistry,
    page_registry: PageRegistry,
    visual_type_registry: VisualTypeRegistry,
    dashlet_registry_: DashletRegistry,
) -> None:
    visual_type_registry.register(VisualTypeDashboards)
    permission_section_registry.register(PermissionSectionDashboard)

    page_registry.register_page("ajax_figure_dashlet_data")(FigureDashletPage)
    page_registry.register_page("ajax_initial_dashboard_filters")(AjaxInitialDashboardFilters)
    page_registry.register_page("edit_dashlet")(EditDashletPage)
    page_registry.register_page_handler("delete_dashlet", page_delete_dashlet)
    page_registry.register_page_handler("dashboard", page_dashboard)
    page_registry.register_page_handler("dashboard_dashlet", ajax_dashlet)
    page_registry.register_page_handler("edit_dashboards", page_edit_dashboards)
    page_registry.register_page_handler("create_dashboard", page_create_dashboard)
    page_registry.register_page_handler("edit_dashboard", page_edit_dashboard)
    page_registry.register_page_handler("create_link_view_dashlet", page_create_link_view_dashlet)
    page_registry.register_page_handler("create_view_dashlet", page_create_view_dashlet)
    page_registry.register_page_handler("create_view_dashlet_infos", page_create_view_dashlet_infos)
    page_registry.register_page_handler("clone_dashlet", page_clone_dashlet)
    page_registry.register_page_handler("delete_dashlet", page_delete_dashlet)
    page_registry.register_page_handler("ajax_dashlet_pos", ajax_dashlet_pos)

    register_dashlets(dashlet_registry_)
    register_builtin_dashboards(builtin_dashboards)


class PermissionSectionDashboard(PermissionSection):
    @property
    def name(self) -> str:
        return "dashboard"

    @property
    def title(self) -> str:
        return _("Dashboards")

    @property
    def do_sort(self):
        return True


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    _register_pre_21_plugin_api()

    # Load plugins for dashboards. Currently these files
    # just may add custom dashboards by adding to builtin_dashboards.
    utils.load_web_plugins("dashboard", globals())

    visuals.declare_visual_permissions("dashboards", _("dashboards"))

    # Declare permissions for all dashboards
    for name, board in builtin_dashboards.items():
        # Special hack for the "main" dashboard: It contains graphs that are only correct in case
        # you are permitted on all hosts and services. All elements on the dashboard are filtered by
        # the individual user permissions. Only the problem graphs are not able to respect these
        # permissions. To not confuse the users we make the "main" dashboard in the enterprise
        # editions only visible to the roles that have the "general.see_all" permission.
        if name == "main" and not cmk_version.is_raw_edition():
            # Please note: This permitts the following roles: ["admin", "guest"]. Even if the user
            # overrides the permissions of these builtin roles in his configuration , this can not
            # be respected here. This is because the config of the user is not loaded yet. The user
            # would have to manually adjust the permissions on the main dashboard on his own.
            default_permissions = permission_registry["general.see_all"].defaults
        else:
            default_permissions = default_authorized_builtin_role_ids

        declare_permission(
            "dashboard.%s" % name,
            board["title"],
            board.get("description", ""),
            default_permissions,
        )

    # Make sure that custom views also have permissions
    declare_dynamic_permissions(lambda: visuals.declare_custom_permissions("dashboards"))
    declare_dynamic_permissions(lambda: visuals.declare_packaged_visuals_permissions("dashboards"))


def _register_pre_21_plugin_api() -> None:
    """Register pre 2.1 "plugin API"

    This was never an official API, but the names were used by builtin and also 3rd party plugins.

    Our builtin plugin have been changed to directly import from the .utils module. We add these old
    names to remain compatible with 3rd party plugins for now.

    In the moment we define an official plugin API, we can drop this and require all plugins to
    switch to the new API. Until then let's not bother the users with it.

    CMK-12228
    """
    # Needs to be a local import to not influence the regular plugin loading order
    import cmk.gui.plugins.dashboard as api_module
    import cmk.gui.plugins.dashboard.utils as plugin_utils

    for name, val in (
        ("ABCFigureDashlet", ABCFigureDashlet),
        ("builtin_dashboards", builtin_dashboards),
        ("Dashlet", Dashlet),
        ("dashlet_registry", dashlet_registry),
        ("GROW", GROW),
        ("IFrameDashlet", IFrameDashlet),
        ("MAX", MAX),
    ):
        api_module.__dict__[name] = plugin_utils.__dict__[name] = val

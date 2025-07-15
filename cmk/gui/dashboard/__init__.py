#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.ccc.version as cmk_version
from cmk.gui import utils, visuals
from cmk.gui.config import default_authorized_builtin_role_ids
from cmk.gui.i18n import _
from cmk.gui.permissions import declare_dynamic_permissions, declare_permission, permission_registry
from cmk.utils import paths

from ._network_topology import get_topology_context_and_filters
from .builtin_dashboards import (
    builtin_dashboard_extender_registry,
    builtin_dashboards,
    BuiltinDashboardExtender,
    BuiltinDashboardExtenderRegistry,
    GROW,
    MAX,
    noop_builtin_dashboard_extender,
)
from .dashlet import (
    ABCFigureDashlet,
    Dashlet,
    dashlet_registry,
    DashletConfig,
    DashletRegistry,
    IFrameDashlet,
    LinkedViewDashletConfig,
    StaticTextDashletConfig,
    ViewDashletConfig,
)
from .store import get_all_dashboards, get_dashlet, get_permitted_dashboards
from .title_macros import render_title_with_macros_string
from .type_defs import DashboardConfig, DashboardName
from .visual_type import VisualTypeDashboards

__all__ = [
    "load_plugins",
    "DashletConfig",
    "DashletRegistry",
    "DashboardName",
    "DashboardConfig",
    "builtin_dashboard_extender_registry",
    "builtin_dashboards",
    "BuiltinDashboardExtender",
    "BuiltinDashboardExtenderRegistry",
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
    "noop_builtin_dashboard_extender",
    "render_title_with_macros_string",
    "ABCFigureDashlet",
    "IFrameDashlet",
    "VisualTypeDashboards",
]


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    _register_pre_21_plugin_api()

    # Load plug-ins for dashboards. Currently these files
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
        if name == "main" and cmk_version.edition(paths.omd_root) is not cmk_version.Edition.CRE:
            # Please note: This permitts the following roles: ["admin", "guest"]. Even if the user
            # overrides the permissions of these built-in roles in his configuration , this can not
            # be respected here. This is because the config of the user is not loaded yet. The user
            # would have to manually adjust the permissions on the main dashboard on his own.
            default_permissions = permission_registry["general.see_all"].defaults
        else:
            default_permissions = default_authorized_builtin_role_ids

        declare_permission(
            "dashboard.%s" % name,
            f"{board['title']} ({board['name']})",
            board.get("description", ""),
            default_permissions,
        )

    # Make sure that custom views also have permissions
    declare_dynamic_permissions(lambda: visuals.declare_custom_permissions("dashboards"))
    declare_dynamic_permissions(lambda: visuals.declare_packaged_visuals_permissions("dashboards"))


def _register_pre_21_plugin_api() -> None:
    """Register pre 2.1 "plugin API"

    This was never an official API, but the names were used by built-in and also 3rd party plugins.

    Our built-in plug-in have been changed to directly import from the .utils module. We add these old
    names to remain compatible with 3rd party plug-ins for now.

    In the moment we define an official plug-in API, we can drop this and require all plug-ins to
    switch to the new API. Until then let's not bother the users with it.

    CMK-12228
    """
    # Needs to be a local import to not influence the regular plug-in loading order
    import cmk.gui.plugins.dashboard as api_module  # pylint: disable=cmk-module-layer-violation
    import cmk.gui.plugins.dashboard.utils as plugin_utils  # pylint: disable=cmk-module-layer-violation

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

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

"""HTML page handler for generating the (a) dashboard. The name
of the dashboard to render is given in the HTML variable 'name'.
"""

from dataclasses import asdict
from typing import Literal

import cmk.ccc.version as cmk_version
from cmk.gui import visuals
from cmk.gui.exceptions import MKAuthException
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import VisualTypeName
from cmk.gui.utils.html import HTML
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.visuals import visual_page_breadcrumb
from cmk.gui.visuals._filter_context import requested_context_from_request
from cmk.utils import paths
from cmk.utils.licensing.registry import get_licensing_user_effect

from .breadcrumb import dashboard_breadcrumb, EvaluatedBreadcrumbItem
from .metadata import DashboardMetadataObject
from .page_edit_dashboards import PAGE_EDIT_DASHBOARDS_LINK
from .store import (
    get_permitted_dashboards,
    load_dashboard,
)

__all__ = ["page_dashboard_app"]


def page_dashboard_app(ctx: PageContext) -> None:
    # edit mode lives within the page
    mode: Literal["display", "create", "clone", "edit_settings", "edit_layout"] = "display"

    if ctx.request.var("mode") == "create":
        if not user.may("general.edit_dashboards"):
            raise MKAuthException(_("You are not allowed to create dashboards."))
        mode = "create"

    elif ctx.request.var("mode") == "clone":
        if not user.may("general.edit_dashboards"):
            raise MKAuthException(_("You are not allowed to clone dashboards."))
        mode = "clone"

    elif ctx.request.var("mode") == "edit_settings":
        if not user.may("general.edit_dashboards"):
            raise MKAuthException(_("You are not allowed to edit dashboards."))
        mode = "edit_settings"

    elif ctx.request.var("mode") == "edit_layout":
        if not user.may("general.edit_dashboards"):
            raise MKAuthException(_("You are not allowed to edit dashboards."))
        mode = "edit_layout"

    name = ctx.request.get_ascii_input_mandatory("name", "")

    if not name:
        name = _get_default_dashboard_name()
        ctx.request.set_var("name", name)  # TODO: this must be done on the frontend side

    loaded_dashboard_properties = None
    if mode == "create":
        visual_name: VisualTypeName = "dashboards"
        title = _("Create dashboard")
        breadcrumb = visual_page_breadcrumb(visual_name, title, "create")
    else:
        permitted_dashboards = get_permitted_dashboards()
        board = load_dashboard(permitted_dashboards, name)
        requested_context = requested_context_from_request(["host", "service"])

        board_context = visuals.active_context_from_request(["host", "service"], board["context"])
        board["context"] = board_context
        title = visuals.visual_title("dashboard", board, board_context)
        user_permissions = UserPermissions.from_config(ctx.config, permission_registry)
        # some dashboards have more complicated context requirements when loaded, these are
        # constructed when clicking on a linking dashboard which means that this will (for now
        # with the current architecture) always go through a full page reload rather than a
        # state changing action. Hence, we can rely on the breadcrumb building mechanism here
        # Loading a dashboard on the frontend through other means will only necessitate the
        # simple breadcrumb as it does not have any prior context
        breadcrumb = dashboard_breadcrumb(name, board, title, board_context, user_permissions)

        loaded_dashboard_properties = {
            "metadata": asdict(
                DashboardMetadataObject.from_dashboard_config(board, user_permissions)
            ),
            "filter_context": {
                "context": requested_context,
                # determines if the requested filters should overwrite the dashboard filters or
                # merge them with dashboard filters
                "application_mode": "overwrite" if ctx.request.has_var("active_") else "merge",
            },
        }

    html.body_start()
    html.begin_page_content(enable_scrollbar=True)

    _may_show_license_messages(ctx.request)

    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.COMMUNITY:
        available_layouts = ["relative_grid"]
        available_features = "restricted"

    else:
        available_layouts = ["relative_grid", "responsive_grid"]
        available_features = "unrestricted"

    page_properties = {
        "initial_breadcrumb": [
            asdict(EvaluatedBreadcrumbItem.from_breadcrumb_item(item)) for item in breadcrumb
        ],
        # TODO: consider adding initial title as well due to context generation
        "dashboard": loaded_dashboard_properties,
        "mode": mode,
        "url_params": {"ifid": ctx.request.get_ascii_input("ifid")},
        "links": {
            "list_dashboards": f"{PAGE_EDIT_DASHBOARDS_LINK}.py",
            "user_guide": "https://docs.checkmk.com/master/en/dashboards.html",
            "navigation_embedding_page": makeuri_contextless(ctx.request, [], filename="index.py"),
        },
        "available_layouts": available_layouts,
        "available_features": available_features,
        "logged_in_user": user.id,
    }

    html.vue_component("cmk-dashboard", data=page_properties)


def _get_default_dashboard_name() -> str:
    """Return the default dashboard name for the current site

    We separate our users into two groups:

    1. Those WITH the permission "see all hosts / service". Which are mainly administrative users.

    These are starting with the main overview dashboard which either shows a site drill down snap-in
    (in case multiple sites are configured) or the hosts of their site (in case there is only a
    single site configured).

    2. Those WITHOUT the permission "see all hosts / service". Which are normal users.

    They will see the dashboard that has been built for operators and is built to show only the host
    and service problems that are relevant for the user.
    """
    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.COMMUNITY:
        return "main"  # problems = main in community edition
    return "main" if user.may("general.see_all") and user.may("dashboard.main") else "problems"


def _may_show_license_messages(request: Request) -> None:
    """Render license warning and banner above the Vue dashboard."""
    user_effect = get_licensing_user_effect(
        makeuri_contextless(request, [("mode", "licensing")], filename="wato.py")
    )

    if (header := user_effect.header) and set(header.roles).intersection(user.role_ids):
        html.show_warning(HTML.without_escaping(header.message_html))

    if (banner := user_effect.banner) and set(banner.roles).intersection(user.role_ids):
        html.write_html(HTML.without_escaping(banner.message_html))

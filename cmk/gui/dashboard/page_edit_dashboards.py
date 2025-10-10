#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.config import Config
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.urls import makeuri_contextless

from .store import get_all_dashboards
from .type_defs import DashboardConfig, DashboardName


def page_edit_dashboards(config: Config) -> None:
    visuals.page_list(
        what="dashboards",
        title=_("Edit dashboards"),
        visuals=get_all_dashboards(),
        user_permissions=UserPermissions.from_config(config, permission_registry),
        render_custom_buttons=_render_dashboard_buttons,
    )


def _render_dashboard_buttons(dashboard_name: DashboardName, dashboard: DashboardConfig) -> None:
    owner = dashboard["owner"]
    if owner == user.id or (
        owner != UserId.builtin() and user.may("general.edit_foreign_dashboards")
    ):
        if dashboard.get("show_title"):
            html.icon_button(
                makeuri_contextless(
                    request,
                    [
                        ("owner", owner),
                        ("name", dashboard_name),
                        ("edit", "1"),
                    ],
                    "dashboard.py",
                ),
                title=_("Edit layout"),
                icon="dashboard",
            )
        else:
            html.icon(
                icon="dashboard",
                title=_("Edit layout only available if header is enabled"),
                cssclass="colorless",
            )

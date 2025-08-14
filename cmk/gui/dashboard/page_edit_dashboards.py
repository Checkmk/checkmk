#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui import visuals
from cmk.gui.config import Config
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.utils.urls import makeuri_contextless

from .store import get_all_dashboards
from .type_defs import DashboardConfig, DashboardName


def page_edit_dashboards(config: Config) -> None:
    visuals.page_list(
        what="dashboards",
        title=_("Edit dashboards"),
        visuals=get_all_dashboards(),
        render_custom_buttons=_render_dashboard_buttons,
    )


def _render_dashboard_buttons(dashboard_name: DashboardName, dashboard: DashboardConfig) -> None:
    if dashboard["owner"] == user.id:
        if dashboard.get("show_title"):
            html.icon_button(
                makeuri_contextless(
                    request,
                    [
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

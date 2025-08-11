#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Configures the global settings of a dashboard"""

import time

from cmk.gui import visuals
from cmk.gui.config import Config
from cmk.gui.i18n import _
from cmk.gui.valuespec import Checkbox, Dictionary

from .store import get_all_dashboards
from .type_defs import DashboardConfig

__all__ = ["page_edit_dashboard"]


def page_edit_dashboard(config: Config) -> None:
    visuals.page_edit_visual(
        "dashboards",
        get_all_dashboards(),
        create_handler=create_dashboard,
        custom_field_handler=dashboard_fields_handler,
        info_handler=_dashboard_info_handler,
        help_text_context=_(
            "A dashboard can have an optional context. It can for example be restricted to display "
            "only information of a single host or for a set of services matching a regular "
            "expression."
        ),
    )


def _dashboard_info_handler(visual):
    # We could use all available infos here, but there is a lot of normally unused stuff. For better
    # usability reduce the list to the (assumed) relevant used ones.
    return ["host", "service"]


def dashboard_fields_handler(dashboard: DashboardConfig) -> None:
    _vs_dashboard().render_input("dashboard", dict(dashboard) if dashboard else None)


def create_dashboard(old_dashboard: DashboardConfig, dashboard: DashboardConfig) -> DashboardConfig:
    vs_dashboard = _vs_dashboard()
    board_properties = vs_dashboard.from_html_vars("dashboard")
    vs_dashboard.validate_value(board_properties, "dashboard")
    # Can hopefully be removed one day once we have improved typing in the valuespecs. Until
    # then we'll have to trust that from_html_vars and validate_value ensure we get the right
    # data.
    dashboard.update(board_properties)  # type: ignore[typeddict-item]

    # Do not remove the dashlet configuration during general property editing
    dashboard["dashlets"] = old_dashboard.get("dashlets", [])
    dashboard["mtime"] = int(time.time())

    return dashboard


def _vs_dashboard() -> Dictionary:
    return Dictionary(
        title=_("Dashboard properties"),
        render="form",
        optional_keys=False,
        elements=[
            (
                "show_title",
                Checkbox(
                    title=_("Display dashboard title"),
                    label=_("Show the header of the dashboard with the configured title."),
                    default_value=True,
                ),
            ),
            (
                "mandatory_context_filters",
                visuals.FilterChoices(
                    # Like _dashboard_info_handler we assume that only host / service filters are relevant
                    infos=["host", "service"],
                    title=_("Required context filters"),
                    help=_(
                        "Show the dialog that can be used to update the dashboard context "
                        "on initial dashboard rendering and enforce the user to provide the "
                        "context filters that are set here. This can be useful in case you want "
                        "the users to first provide some context before rendering the dashboard."
                    ),
                ),
            ),
        ],
        form_isopen=False,
        help=_(
            "Here, you can configure additional properties of the dashboard. This is completely "
            "optional and only needed to create more advanced dashboards. For example, you can "
            "make certain filters mandatory. This enables you to build generic dashboards which "
            "could for example contain all the relevant information for a single Oracle DB. "
            "However, before the dashboard is rendered, the user has to decide which DB he wants "
            "to look at."
        ),
    )

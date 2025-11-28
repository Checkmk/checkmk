#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import cast, override

from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.dashboard import DashboardConfig, DashboardName, get_all_dashboards
from cmk.gui.dashboard.metadata import dashboard_uses_relative_grid
from cmk.gui.dashboard.type_defs import DashletConfig, EmbeddedViewDashletConfig, ViewDashletConfig
from cmk.gui.type_defs import DashboardEmbeddedViewSpec
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction


class MigrateUserDashboards(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        all_dashboards = get_all_dashboards()
        migrated_dashboards: dict[UserId, list[tuple[DashboardName, DashboardConfig]]] = {}
        for (owner, dashboard_name), dashboard in all_dashboards.items():
            owner_dashboards = migrated_dashboards.setdefault(owner, list())

            # ensure required fields exist
            dashboard.setdefault("single_infos", [])
            dashboard.setdefault("context", {})
            dashboard.setdefault("mandatory_context_filters", [])

            if not dashboard_uses_relative_grid(dashboard):
                # responsive dashboard always uses the new view format already
                owner_dashboards.append((dashboard_name, dashboard))
                continue

            dashlets, embedded_views = self.migrate_dashlets(dashboard)
            dashboard["dashlets"] = dashlets
            dashboard["embedded_views"] = embedded_views
            owner_dashboards.append((dashboard_name, dashboard))

        for owner, dashboards in migrated_dashboards.items():
            owner_migrated_dashboards = {
                (owner, dashboard_name): dashboard for (dashboard_name, dashboard) in dashboards
            }
            visuals.save("dashboards", owner_migrated_dashboards, owner)

    @staticmethod
    def migrate_dashlets(
        dashboard: DashboardConfig,
    ) -> tuple[list[DashletConfig], dict[str, DashboardEmbeddedViewSpec]]:
        embedded_views = dashboard.get("embedded_views", dict())
        dashlets: list[DashletConfig] = []
        for dashlet in dashboard["dashlets"]:
            if dashlet["type"] != "view":
                dashlets.append(dashlet)
                continue

            dashlet = cast(ViewDashletConfig, dashlet)
            view_name = dashlet["name"]
            dashlet_embedded_view: EmbeddedViewDashletConfig = {
                "name": view_name,
                "datasource": dashlet["datasource"],
                "single_infos": dashlet["single_infos"],
                # position and size are expected since we are in a relative dashboard context
                "position": dashlet["position"],
                "size": dashlet["size"],
                "type": "embedded_view",
            }
            if "background" in dashlet:
                dashlet_embedded_view["background"] = dashlet["background"]

            if "context" in dashlet:
                dashlet_embedded_view["context"] = dashlet["context"]

            if "title" in dashlet:
                dashlet_embedded_view["title"] = dashlet["title"]

            if "show_title" in dashlet:
                dashlet_embedded_view["show_title"] = dashlet["show_title"]

            embedded_view: DashboardEmbeddedViewSpec = {
                "single_infos": dashlet["single_infos"],
                "datasource": dashlet["datasource"],
                "layout": dashlet["layout"],
                "group_painters": dashlet["group_painters"],
                "painters": dashlet["painters"],
                "browser_reload": dashlet["browser_reload"],
                "num_columns": dashlet["num_columns"],
                "column_headers": dashlet["column_headers"],
                "sorters": dashlet["sorters"],
            }

            if "add_headers" in dashlet:
                embedded_view["add_headers"] = dashlet["add_headers"]

            if "mobile" in dashlet:
                embedded_view["mobile"] = dashlet["mobile"]

            if "mustsearch" in dashlet:
                embedded_view["mustsearch"] = dashlet["mustsearch"]

            if "force_checkboxes" in dashlet:
                embedded_view["force_checkboxes"] = dashlet["force_checkboxes"]

            if "user_sortable" in dashlet:
                embedded_view["user_sortable"] = dashlet["user_sortable"]

            if "play_sounds" in dashlet:
                embedded_view["play_sounds"] = dashlet["play_sounds"]

            if "inventory_join_macros" in dashlet:
                embedded_view["inventory_join_macros"] = dashlet["inventory_join_macros"]

            embedded_views[view_name] = embedded_view
            dashlets.append(dashlet_embedded_view)

        return dashlets, embedded_views


update_action_registry.register(
    MigrateUserDashboards(
        name="migrate_user_dashboards",
        title="Migrate user dashboards",
        sort_index=200,  # no order importance
        expiry_version=ExpiryVersion.NEVER,
    )
)

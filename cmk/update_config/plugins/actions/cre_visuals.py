#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from logging import Logger
from typing import cast

from cmk.gui.dashboard import get_all_dashboards
from cmk.gui.dashboard.dashlet.dashlets.graph import (
    TemplateGraphDashlet,
    TemplateGraphDashletConfig,
)
from cmk.gui.dashboard.type_defs import DashletConfig
from cmk.gui.views.store import get_all_views

from cmk.update_config.plugins.actions.visuals_utils import save_user_visuals, update_visuals
from cmk.update_config.plugins.lib.graph_templates import RENAMED_GRAPH_TEMPLATES
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateViews(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        update_visuals("views", get_all_views())


class UpdateDashboards(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        dashboards = get_all_dashboards()
        update_visuals("dashboards", dashboards)

        with save_user_visuals("dashboards", dashboards) as affected_users:
            for (owner, _dashboard_name), dashboard_config in dashboards.items():
                if not owner:
                    continue
                affected_users.add(owner)
                for dashlet_config in dashboard_config["dashlets"]:
                    self._update_dashlet_config(dashlet_config)

    def _update_dashlet_config(self, dashlet_config: DashletConfig) -> None:
        if dashlet_config["type"] == TemplateGraphDashlet.type_name():
            _update_graph_template_in_template_graph_dashlet(
                cast(TemplateGraphDashletConfig, dashlet_config),
                RENAMED_GRAPH_TEMPLATES,
            )


update_action_registry.register(
    UpdateViews(
        name="views",
        title="Update views",
        sort_index=10,
    )
)

update_action_registry.register(
    UpdateDashboards(
        name="dashboards",
        title="Update dashboards",
        sort_index=11,
    )
)


def _update_graph_template_in_template_graph_dashlet(
    dashlet_config: TemplateGraphDashletConfig,
    renamed_graph_templates: Mapping[str, str],
) -> TemplateGraphDashletConfig:
    dashlet_config["source"] = renamed_graph_templates.get(
        dashlet_config["source"],
        dashlet_config["source"],
    )
    return dashlet_config

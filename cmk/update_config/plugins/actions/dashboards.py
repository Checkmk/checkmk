#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from logging import Logger
from typing import cast, override

from cmk.ccc.user import UserId

from cmk.gui import visuals
from cmk.gui.dashboard import get_all_dashboards
from cmk.gui.dashboard.dashlet.dashlets.graph import (
    TemplateGraphDashlet,
    TemplateGraphDashletConfig,
)
from cmk.gui.dashboard.type_defs import DashboardConfig, DashletConfig

from cmk.update_config.plugins.lib.graph_templates import RENAMED_GRAPH_TEMPLATES
from cmk.update_config.registry import update_action_registry, UpdateAction


class UpdateDashboards(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        dashboards = get_all_dashboards()
        with save_user_dashboards(dashboards) as affected_users:
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
    UpdateDashboards(
        name="dashboards",
        title="Update dashboards",
        sort_index=11,
    )
)


@contextmanager
def save_user_dashboards(
    all_dashboards: dict[tuple[UserId, str], DashboardConfig],
) -> Iterator[set[UserId]]:
    users_with_modified_instances: set[UserId] = set()
    try:
        yield users_with_modified_instances
    finally:
        for user_id in users_with_modified_instances:
            visuals.save("dashboards", all_dashboards, user_id)


def _update_graph_template_in_template_graph_dashlet(
    dashlet_config: TemplateGraphDashletConfig,
    renamed_graph_templates: Mapping[str, str],
) -> TemplateGraphDashletConfig:
    dashlet_config["source"] = renamed_graph_templates.get(
        dashlet_config["source"],
        dashlet_config["source"],
    )
    return dashlet_config

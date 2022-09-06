#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.gui.plugins.dashboard.utils import get_all_dashboards
from cmk.gui.view_store import get_all_views

from cmk.update_config.plugins.actions.visuals_utils import update_visuals
from cmk.update_config.registry import update_action_registry, UpdateAction


class UpdateViews(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        update_visuals("views", get_all_views())


class UpdateDashboards(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        update_visuals("dashboards", get_all_dashboards())


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

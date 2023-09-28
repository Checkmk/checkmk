#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.gui.dashboard import get_all_dashboards
from cmk.gui.views.store import get_all_views

from cmk.update_config.plugins.actions.visuals_utils import update_visuals
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateViews(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        update_visuals("views", get_all_views())


class UpdateDashboards(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
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

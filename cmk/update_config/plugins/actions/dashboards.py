#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.ccc.user import UserId
from cmk.gui.dashboard import DashboardConfig
from cmk.gui.dashboard.store import DashboardStore
from cmk.gui.visuals import invalidate_all_caches, save
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction


class MigrateDashboardConfig(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        invalidate_all_caches()
        # creating a new DashboardStore just to make sure we don't use cached results
        all_dashboards = DashboardStore().all
        # the migration should now have happened, since it's executed at runtime for all dashboards
        # we just need to save the results back to file, grouped by user
        by_user: dict[UserId, dict[tuple[UserId, str], DashboardConfig]] = {}
        for (user_id, name), dashboard_config in all_dashboards.items():
            by_user.setdefault(user_id, {})[(user_id, name)] = dashboard_config

        for user_id, dashboards in by_user.items():
            save("dashboards", dashboards, user_id)


update_action_registry.register(
    MigrateDashboardConfig(
        name="migrate_dashboard_config",
        title="Migrate user dashboards to the new config format",
        sort_index=110,  # after older visual migrations
        expiry_version=ExpiryVersion.CMK_260,
    )
)

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import cast, override

import cmk.utils.paths
from cmk.ccc import store
from cmk.gui.dashboard.store import migrate_widget_time_range
from cmk.gui.dashboard.type_defs import DashletConfig
from cmk.update_config.internal import ExpiryVersion, UpdateAction
from cmk.update_config.plugins.lib.user_profiles import user_directories
from cmk.update_config.registry import update_action_registry


def _as_dict(value: object, what: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"expected {what} to be a dict, got {value!r}")
    return value


def _migrate_widget(widget: object) -> object:
    parsed = _as_dict(widget, "a widget")
    if "type" not in parsed:
        raise KeyError("type")
    return migrate_widget_time_range(cast(DashletConfig, parsed))


def _migrate_dashboard(dashboard: object) -> dict[str, object]:
    parsed = _as_dict(dashboard, "a dashboard")
    migrated = dict(parsed)
    if "widgets" in parsed:
        widgets = _as_dict(parsed["widgets"], "the widgets of a dashboard")
        migrated["widgets"] = {
            widget_id: _migrate_widget(widget) for widget_id, widget in widgets.items()
        }
    # Dashboards nobody saved since the "widgets" field came still list their "dashlets"
    if isinstance(dashlets := parsed.get("dashlets"), list):
        migrated["dashlets"] = [_migrate_widget(widget) for widget in dashlets]
    return migrated


def _with_migrated_time_ranges(dashboards: dict[str, object]) -> dict[str, object]:
    return {name: _migrate_dashboard(dashboard) for name, dashboard in dashboards.items()}


class MigrateDashboardWidgetTimeRange(UpdateAction):
    """Store the time range of the graph and scatterplot widgets of 2.5 as Inherit or Override."""

    @override
    def __call__(self, logger: Logger, *, debug: bool) -> None:
        self.migrate_time_ranges(cmk.utils.paths.profile_dir, logger, debug=debug)

    @staticmethod
    def migrate_time_ranges(profile_dir: Path, logger: Logger, *, debug: bool) -> None:
        migrated = 0
        for user_dir in user_directories(profile_dir):
            path = user_dir / "user_dashboards.mk"
            dashboards = store.load_object_from_file(path, default={}, debug=debug)
            try:
                converted = _with_migrated_time_ranges(_as_dict(dashboards, "the dashboards"))
            except (TypeError, KeyError) as exc:
                raise ValueError(f"Unexpected format in {path}: {exc}") from exc

            if changed := sum(1 for name, board in dashboards.items() if converted[name] != board):
                store.save_object_to_file(path, converted)
                migrated += changed

        if migrated:
            logger.info(
                "Migrated the widget time ranges of %(count)d dashboards",
                {"count": migrated},
            )


update_action_registry.register(
    MigrateDashboardWidgetTimeRange(
        name="migrate_dashboard_widget_time_range",
        title="Migrate the time range of graph and scatterplot widgets to Inherit or Override",
        sort_index=105,  # after the render options cleanup, before migrate_dashboard_config
        expiry_version=ExpiryVersion.CMK_310,
    )
)

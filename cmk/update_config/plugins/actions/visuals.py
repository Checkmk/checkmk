#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from logging import Logger
from typing import Final, override

from cmk.ccc.user import UserId
from cmk.gui.dashboard.store import get_all_dashboards
from cmk.gui.type_defs import Visual, VisualName
from cmk.gui.views.inventory import (
    FilterMigration,
    find_non_canonical_filters,
    load_inventory_ui_plugins,
)
from cmk.gui.views.inventory.registry import inventory_displayhints
from cmk.gui.views.store import get_all_views
from cmk.gui.visuals import save, TVisual
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction


class Migration:
    def __init__(self, visuals: Mapping[tuple[UserId, VisualName], Visual]) -> None:
        self._visuals: Final = visuals
        self._migrated: Mapping[tuple[UserId, VisualName], Visual] = {}
        self._has_changed = False

    def _migrate_visual(
        self, visual: TVisual, non_canonical_filters: Mapping[str, FilterMigration]
    ) -> TVisual:
        if not (context := visual.get("context")):
            return visual

        assert isinstance(context, dict)
        migrated = {}
        for filter_ident, filter_vars in context.items():
            if filter_migration := non_canonical_filters.get(filter_ident):
                migrated[filter_migration.name] = filter_migration(filter_vars)
            else:
                migrated[filter_ident] = filter_vars

        if context != migrated:
            self._has_changed = True

        visual["context"] = migrated
        return visual

    def __call__(self, non_canonical_filters: Mapping[str, FilterMigration]) -> None:
        self._migrated = {
            key: self._migrate_visual(visual, non_canonical_filters)
            for key, visual in self._visuals.items()
        }

    @property
    def migrated(self) -> Mapping[UserId, dict[tuple[UserId, VisualName], Visual]]:
        by_users: dict[UserId, dict[tuple[UserId, VisualName], Visual]] = {}
        for key, visual in self._migrated.items():
            by_users.setdefault(key[0], {}).setdefault(key, visual)
        return by_users

    @property
    def has_changed(self) -> bool:
        return self._has_changed


def migrate_visuals(
    visuals: Mapping[tuple[UserId, VisualName], Visual],
    non_canonical_filters: Mapping[str, FilterMigration],
) -> Migration:
    migration = Migration(visuals)
    migration(non_canonical_filters)
    return migration


class MigrateVisualsInventoryFilters(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        non_canonical_filters = find_non_canonical_filters(
            load_inventory_ui_plugins(), inventory_displayhints
        )

        if (
            migrated_dashboards := migrate_visuals(get_all_dashboards(), non_canonical_filters)
        ).has_changed:
            for user_id, visuals in migrated_dashboards.migrated.items():
                save("dashboards", visuals, user_id)

        if (migrated_views := migrate_visuals(get_all_views(), non_canonical_filters)).has_changed:
            for user_id, visuals in migrated_views.migrated.items():
                save("views", visuals, user_id)


update_action_registry.register(
    MigrateVisualsInventoryFilters(
        name="migrate_visuals_inventory_filters",
        title="Migrate filters of HW/SW Inventory based views or dashboards",
        sort_index=100,  # don't care
        expiry_version=ExpiryVersion.CMK_300,
    )
)

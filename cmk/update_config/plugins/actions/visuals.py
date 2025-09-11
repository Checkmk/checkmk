#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from logging import Logger
from typing import override

from cmk.ccc.user import UserId
from cmk.gui.dashboard.store import get_all_dashboards
from cmk.gui.type_defs import Visual
from cmk.gui.views.inventory import find_non_canonical_filters
from cmk.gui.views.inventory.registry import inventory_displayhints
from cmk.gui.views.store import get_all_views
from cmk.gui.visuals import save, TVisual
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction


def _migrate_context_value(key: str, value: Mapping[str, str], scale: int) -> Mapping[str, str]:
    migrated = {}
    for direction in ("from", "until"):
        if filter_value := value.get(f"{key}_{direction}"):
            migrated[f"{key}_canonical_{direction}"] = str(int(filter_value) * scale)
    return migrated


def _migrate_visual(visual: TVisual, non_canonical_filters: Mapping[str, int]) -> TVisual:
    if not (context := visual.get("context")):
        return visual
    assert isinstance(context, dict)
    migrated = {}
    for key, value in context.items():
        if key in non_canonical_filters and (
            value_ := _migrate_context_value(key, value, non_canonical_filters[key])
        ):
            migrated[key] = value_
        else:
            migrated[key] = value
    visual["context"] = migrated
    return visual


def migrate_visuals(
    visuals: Mapping[tuple[UserId, str], Visual], non_canonical_filters: Mapping[str, int]
) -> Mapping[tuple[UserId, str], Visual]:
    return {
        name: _migrate_visual(visual, non_canonical_filters) for name, visual in visuals.items()
    }


class MigrateVisualsInvAttrFilter(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        non_canonical_filters = find_non_canonical_filters(inventory_displayhints)

        dashboards = get_all_dashboards()
        if dashboards != (
            migrated_dashboards := migrate_visuals(dashboards, non_canonical_filters)
        ):
            save("dashboards", dict(migrated_dashboards))

        views = get_all_views()
        if views != (migrated_views := migrate_visuals(views, non_canonical_filters)):
            save("views", dict(migrated_views))


update_action_registry.register(
    MigrateVisualsInvAttrFilter(
        name="migrate_visuals_inv_attr_filter",
        title="Migrate attribute filters of HW/SW Inventory based views or dashboards",
        sort_index=100,  # don't care
        expiry_version=ExpiryVersion.CMK_260,
    )
)

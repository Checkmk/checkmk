#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="unreachable"

from logging import Logger
from typing import override

from cmk.ccc.user import UserId
from cmk.gui.type_defs import AllViewSpecs
from cmk.gui.views.store import get_all_views
from cmk.gui.visuals import save
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction


class UpdateViews(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        all_views: AllViewSpecs = get_all_views()
        # Each user has a config file with all their views.
        # We need to group them by user_id to save them later
        # all together, otherwise we may loose views.
        user_views: dict[UserId, AllViewSpecs] = {}
        # Only config files of users who have migrated views need to be overwritten.
        users_to_update: set[UserId] = set()
        builtin_user_id = UserId.builtin()

        for (user_id, view_name), view_dict in all_views.items():
            if user_id == builtin_user_id:
                continue
            column_headers = view_dict.get("column_headers", None)
            if column_headers == "repeat":  # type: ignore[comparison-overlap]
                view_dict["column_headers"] = "pergroup"
                users_to_update.add(user_id)
            user_views.setdefault(user_id, {})
            user_views[user_id][(user_id, view_name)] = view_dict

        for user_id in users_to_update:
            save("views", user_views[user_id], user_id=user_id)


update_action_registry.register(
    UpdateViews(
        name="migrate_view_column_headers",
        title="Migrate view column_headers 'repeat' to 'pergroup'",
        sort_index=130,
        expiry_version=ExpiryVersion.CMK_300,
        continue_on_failure=True,
    )
)

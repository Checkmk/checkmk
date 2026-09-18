#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from logging import Logger
from pathlib import Path
from typing import Final, override

import cmk.utils.paths
from cmk.ccc import store
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.lib.user_profiles import user_directories
from cmk.update_config.registry import update_action_registry, UpdateAction

_RENAMED_SNAPINS: Final[Mapping[str, str]] = {"metric_backend": "telemetry_metrics"}


class RenameSidebarSnapins(UpdateAction):
    """Rename sidebar element type ids; the user configuration silently drops unknown ones."""

    @override
    def __call__(self, logger: Logger) -> None:
        self.rename_snapins(cmk.utils.paths.profile_dir, logger)

    @staticmethod
    def rename_snapins(profile_dir: Path, logger: Logger) -> None:
        renamed = 0
        for user_dir in user_directories(profile_dir):
            path = user_dir / "sidebar.mk"
            config = store.load_object_from_file(path, default=None)
            if not isinstance(config, dict) or not isinstance(
                snapins := config.get("snapins"), list
            ):
                continue
            changed = False
            for snapin in snapins:
                if not isinstance(snapin, dict):
                    continue
                type_id = snapin.get("snapin_type_id")
                if (
                    isinstance(type_id, str)
                    and (new_id := _RENAMED_SNAPINS.get(type_id)) is not None
                ):
                    snapin["snapin_type_id"] = new_id
                    changed = True
            if changed:
                store.save_object_to_file(path, config)
                renamed += 1

        if renamed:
            logger.info(
                "Renamed sidebar elements in %(count)d user configurations", {"count": renamed}
            )


update_action_registry.register(
    RenameSidebarSnapins(
        name="rename_sidebar_snapins",
        title="Rename sidebar elements in user configurations",
        sort_index=100,  # no ordering constraints
        expiry_version=ExpiryVersion.CMK_310,
    )
)

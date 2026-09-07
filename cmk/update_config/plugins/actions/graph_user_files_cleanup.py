#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from itertools import chain
from logging import Logger
from pathlib import Path
from typing import override

import cmk.utils.paths
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.lib.user_profiles import user_directories
from cmk.update_config.registry import update_action_registry, UpdateAction


class RemoveOrphanedGraphUserFiles(UpdateAction):
    """Remove the per-user files left behind by the former graph renderer.

    It was the only reader and writer of the graph size ("graph_size.mk") and of the
    manually dragged range of a custom graph ("graph_range_<custom_graph_id>.mk").
    The current engine takes the size from the render options and keeps the range in
    the graph definition itself, so both files are dead and nothing deletes them.
    """

    @override
    def __call__(self, logger: Logger) -> None:
        self.remove_orphaned_files(cmk.utils.paths.profile_dir, logger)

    @staticmethod
    def remove_orphaned_files(profile_dir: Path, logger: Logger) -> None:
        removed = 0
        for user_dir in user_directories(profile_dir):
            # "graph_pin.mk" is still in use, so do not widen these patterns to "graph_*".
            for path in chain(
                user_dir.glob("graph_size.mk"),
                user_dir.glob("graph_range_*.mk"),
            ):
                try:
                    path.unlink()
                except OSError:
                    logger.debug("Could not delete %(path)s", {"path": path}, exc_info=True)
                else:
                    removed += 1

        if removed:
            logger.info("Removed %(count)d orphaned graph files", {"count": removed})


update_action_registry.register(
    RemoveOrphanedGraphUserFiles(
        name="remove_orphaned_graph_user_files",
        title="Remove orphaned per-user graph files",
        sort_index=101,  # no ordering constraints
        expiry_version=ExpiryVersion.CMK_310,
    )
)

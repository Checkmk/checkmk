#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from logging import Logger
from typing import override

import cmk.utils.paths
from cmk.ccc import store
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.log import VERBOSE


class MigrateDistributedWato(UpdateAction):
    """Migrate distributed_wato.mk file to rename is_wato_slave_site to is_distributed_setup_remote_site"""

    @override
    def __call__(self, logger: Logger) -> None:
        distributed_wato_file = cmk.utils.paths.check_mk_config_dir / "distributed_wato.mk"

        if not distributed_wato_file.exists():
            logger.log(VERBOSE, "No distributed_wato.mk file found, skipping migration")
            return

        try:
            content = store.load_text_from_file(distributed_wato_file, lock=True)

            updated_content = re.sub(
                r"\bis_wato_slave_site\b", "is_distributed_setup_remote_site", content
            )

            if updated_content != content:
                store.save_text_to_file(distributed_wato_file, updated_content)
                logger.log(
                    VERBOSE,
                    "Successfully migrated variable names in distributed_wato.mk",
                )
            else:
                logger.log(VERBOSE, "No changes needed in distributed_wato.mk")

        except Exception as e:
            logger.error(f"Failed to migrate distributed_wato.mk: {e}")


update_action_registry.register(
    MigrateDistributedWato(
        name="migrate_distributed_wato",
        title="Migrate distributed_wato.mk variable names",
        sort_index=1,  # Rename has to happen before any action that might read the file
        expiry_version=ExpiryVersion.CMK_300,
    )
)

#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

import cmk.utils.paths
from cmk.ec.settings import create_paths  # astrein: disable=cmk-module-layer-violation
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction


class RemoveECHistoryBackups(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        history_dir = create_paths(cmk.utils.paths.omd_root).history_dir.value
        for file in history_dir.glob("*.bak"):
            file.unlink()
            logger.debug("Removed file %s", file)


update_action_registry.register(
    RemoveECHistoryBackups(
        name="delete_ec_history_backups",
        title="Event Console: Removing temporary migration backup files",
        sort_index=136,
        expiry_version=ExpiryVersion.CMK_300,
    )
)

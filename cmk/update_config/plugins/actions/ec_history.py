#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import override

import cmk.utils.paths  # pylint: disable=cmk-module-layer-violation

# pylint: disable-next=cmk-module-layer-violation
from cmk.ec.update_config import history_files_to_sqlite
from cmk.update_config.registry import update_action_registry, UpdateAction


class UpdateECHistory(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        self.history_files_to_sqlite(cmk.utils.paths.omd_root, logger)

    @staticmethod
    def history_files_to_sqlite(omd_root: Path, logger: Logger) -> None:
        history_files_to_sqlite(omd_root, logger)


update_action_registry.register(
    UpdateECHistory(
        name="update_ec_history",
        title="Event Console: Migrate history files to sqlite",
        sort_index=135,
    )
)

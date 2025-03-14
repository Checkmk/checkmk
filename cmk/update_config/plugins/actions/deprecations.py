#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path

import cmk.utils.paths

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class ResetDeprecationsScheduling(UpdateAction):  # pylint: disable=too-few-public-methods
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        Path(cmk.utils.paths.var_dir, "deprecations", ".last_run").unlink(missing_ok=True)


update_action_registry.register(
    ResetDeprecationsScheduling(
        name="reset_deprecations_scheduling",
        title="Reset deprecations scheduling",
        sort_index=200,
    )
)

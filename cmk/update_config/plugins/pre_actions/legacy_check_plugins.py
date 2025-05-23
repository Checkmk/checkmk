#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.utils.paths import local_checks_dir

from cmk.base.config import load_and_convert_legacy_checks

from cmk.gui.exceptions import MKUserError

from cmk.agent_based.legacy import find_plugin_files
from cmk.update_config.plugins.pre_actions.utils import (
    ConflictMode,
    continue_per_users_choice,
    Resume,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction


class PreUpdateLegacyCheckPlugins(PreUpdateAction):
    """Load all legacy checks plugins before the real update happens"""

    @override
    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        err_list, _sections, _checks = load_and_convert_legacy_checks(
            find_plugin_files(local_checks_dir)
        )
        if errors := "".join(err_list):
            logger.error(errors)
            if _continue_on_incomp_legacy_check(conflict_mode).is_abort():
                raise MKUserError(None, "incompatible local legacy check file(s)")


def _continue_on_incomp_legacy_check(conflict_mode: ConflictMode) -> Resume:
    match conflict_mode:
        case ConflictMode.FORCE:
            return Resume.UPDATE
        case ConflictMode.ABORT:
            return Resume.ABORT
        case ConflictMode.INSTALL | ConflictMode.KEEP_OLD:
            return Resume.ABORT
        case ConflictMode.ASK:
            return continue_per_users_choice(
                "You can abort the update process (A) and try to fix the incompatibilities or "
                "continue the update (c).\n\nAbort the update process? [A/c] \n",
            )


pre_update_action_registry.register(
    PreUpdateLegacyCheckPlugins(
        name="legacy_check_plugins",
        title="Legacy check plug-ins",
        sort_index=0,
    )
)

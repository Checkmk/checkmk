#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.utils.paths import local_checks_dir

from cmk.base.check_api import get_check_api_context
from cmk.base.config import load_checks, plugin_pathnames_in_directory

from cmk.gui.exceptions import MKUserError

from cmk.update_config.plugins.pre_actions.utils import ConflictMode, continue_per_users_choice
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction


class PreUpdateLegacyCheckPlugins(PreUpdateAction):
    """Load all legacy checks plugins before the real update happens"""

    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        errors = "".join(
            load_checks(get_check_api_context, plugin_pathnames_in_directory(str(local_checks_dir)))
        )
        if errors and not continue_per_users_choice(
            conflict_mode,
            f"{errors}\n"
            "You can abort the update process (A) and try to fix "
            "the incompatibilities or continue the update (c).\n\n"
            "Abort the update process? [A/c] \n",
        ):
            raise MKUserError(None, "incompatible local legacy check file(s)")


pre_update_action_registry.register(
    PreUpdateLegacyCheckPlugins(
        name="legacy_check_plugins",
        title="Legacy check plugins",
        sort_index=0,
    )
)

#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from logging import Logger

from cmk.gui.exceptions import MKUserError

from cmk.update_config.plugins.pre_actions.utils import (
    AUTOCHECK_REWRITE_PREACTION_SORT_INDEX,
    ConflictMode,
    continue_per_users_choice,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction

from ..lib.autochecks import rewrite_yielding_errors


class PreUpdateAgentBasedPlugins(PreUpdateAction):
    """Load all agent based plugins before the real update happens"""

    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        for error in rewrite_yielding_errors(write=False):
            if continue_per_users_choice(
                conflict_mode,
                f"{error.host_name}: {error.message}."
                " You can abort and fix this manually."
                " If you continue, the affected service(s) will be lost, but can be rediscovered."
                " Abort the update process? [A/c] \n",
            ):
                continue
            raise MKUserError(None, "Failed to migrate autochecks")


pre_update_action_registry.register(
    PreUpdateAgentBasedPlugins(
        name="autochecks",
        title="Autochecks",
        sort_index=AUTOCHECK_REWRITE_PREACTION_SORT_INDEX,
    )
)

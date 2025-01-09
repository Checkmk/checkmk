#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import itertools
from logging import Logger

from cmk.utils.hostaddress import HostName
from cmk.utils.log import VERBOSE

from cmk.checkengine.checking import CheckPluginName

from cmk.gui.exceptions import MKUserError

from cmk.update_config.plugins.pre_actions.utils import (
    AUTOCHECK_REWRITE_PREACTION_SORT_INDEX,
    ConflictMode,
    continue_per_users_choice,
    Resume,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction

from ..lib.autochecks import rewrite_yielding_errors


class PreUpdateAgentBasedPlugins(PreUpdateAction):
    """Load all agent based plugins before the real update happens"""

    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        plugin_errors: dict[CheckPluginName, dict[HostName, list[str]]] = {}

        for error in rewrite_yielding_errors(write=False):
            if error.plugin is None:
                logger.error(f"{error.host_name}: {error.message}.")
                if _continue_on_failed_to_migrate(
                    " You can abort and fix this manually."
                    " If you continue, the affected service(s) will be lost, but can be rediscovered."
                    " Abort the update process? [A/c] \n",
                    conflict_mode,
                ).is_not_abort():
                    continue
                raise MKUserError(None, "Failed to migrate autochecks")

            plugin_errors.setdefault(error.plugin, {}).setdefault(error.host_name, []).append(
                error.message
            )

        # show one error per plugin to decrease the number of errors user has to handle
        for plugin, hosts in plugin_errors.items():
            logger.log(VERBOSE, f"{plugin}: Failed to migrate autochecks")
            for host, messages in hosts.items():
                logger.log(VERBOSE, f"  {len(messages)} service(s) on {host} affected")

            all_messages = list(itertools.chain(*hosts.values()))

            logger.error(f"{plugin}: {all_messages[0]}. ")
            if _continue_on_failed_to_migrate(
                "You can abort and fix this manually. "
                f"If you continue, {len(all_messages)} service(s) on {len(hosts)} host(s) will be lost, but can be rediscovered."
                " Abort the update process? [A/c] \n",
                conflict_mode,
            ).is_abort():
                raise MKUserError(None, "Failed to migrate autochecks")


def _continue_on_failed_to_migrate(prompt: str, conflict_mode: ConflictMode) -> Resume:
    match conflict_mode:
        case ConflictMode.FORCE:
            return Resume.UPDATE
        case ConflictMode.ABORT:
            return Resume.ABORT
        case ConflictMode.INSTALL | ConflictMode.KEEP_OLD:
            return Resume.ABORT
        case ConflictMode.ASK:
            return continue_per_users_choice(prompt)


pre_update_action_registry.register(
    PreUpdateAgentBasedPlugins(
        name="autochecks",
        title="Autochecks",
        sort_index=AUTOCHECK_REWRITE_PREACTION_SORT_INDEX,
    )
)

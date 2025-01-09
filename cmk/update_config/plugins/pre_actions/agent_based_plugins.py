#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback
from logging import Logger
from pathlib import Path

from cmk.utils.plugin_loader import load_plugins_with_exceptions

from cmk.gui.exceptions import MKUserError

from cmk.mkp_tool import PackageID
from cmk.update_config.plugins.pre_actions.utils import (
    AGENT_BASED_PLUGINS_PREACTION_SORT_INDEX,
    ConflictMode,
    continue_per_users_choice,
    disable_incomp_mkp,
    error_message_incomp_local_file,
    get_installer_and_package_map,
    get_path_config,
    is_applicable_mkp,
    PACKAGE_STORE,
    Resume,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction


class PreUpdateAgentBasedPlugins(PreUpdateAction):
    """Load all agent based plugins before the real update happens"""

    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        while self._disable_failure_and_reload_plugins(logger, conflict_mode):
            pass

    def _disable_failure_and_reload_plugins(
        self,
        logger: Logger,
        conflict_mode: ConflictMode,
    ) -> bool:
        path_config = get_path_config()
        # This means MKP are not supported so we bail out early
        if path_config is None:
            return False
        package_store = PACKAGE_STORE
        installer, package_map = get_installer_and_package_map(path_config)
        dealt_with_packages: set[PackageID] = set()

        for module_name, error in load_plugins_with_exceptions("cmk.base.plugins.agent_based"):
            path = Path(traceback.extract_tb(error.__traceback__)[-1].filename)
            manifest = package_map.get(path.resolve())
            # unpackaged files
            if manifest is None:
                logger.error(error_message_incomp_local_file(path, error))
                if _continue_on_incomp_local_file(conflict_mode).is_not_abort():
                    continue
                raise MKUserError(None, "incompatible local file")

            if manifest.id in dealt_with_packages:
                continue

            if not is_applicable_mkp(manifest):
                dealt_with_packages.add(manifest.id)
                logger.info(
                    "[%s %s]: Ignoring problems (MKP will be disabled on target version)",
                    manifest.name,
                    manifest.version,
                )
                continue

            if disable_incomp_mkp(
                logger,
                conflict_mode,
                module_name,
                error,
                manifest.id,
                installer,
                package_store,
                path_config,
                path,
            ):
                dealt_with_packages.add(manifest.id)
                return True

            raise MKUserError(None, "incompatible local file")

        return False


def _continue_on_incomp_local_file(conflict_mode: ConflictMode) -> Resume:
    match conflict_mode:
        case ConflictMode.FORCE:
            return Resume.UPDATE
        case ConflictMode.ABORT:
            return Resume.ABORT
        case ConflictMode.INSTALL | ConflictMode.KEEP_OLD:
            return Resume.ABORT
        case ConflictMode.ASK:
            return continue_per_users_choice(
                "You can abort the update process (A) and try to fix "
                "the incompatibilities or continue the update (c).\n\n"
                "Abort the update process? [A/c] \n",
            )


pre_update_action_registry.register(
    PreUpdateAgentBasedPlugins(
        name="agent_based_plugins",
        title="Agent based plugins",
        sort_index=AGENT_BASED_PLUGINS_PREACTION_SORT_INDEX,
    )
)

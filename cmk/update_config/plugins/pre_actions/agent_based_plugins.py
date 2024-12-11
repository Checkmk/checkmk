#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from logging import Logger
from pathlib import Path

from cmk.utils.paths import local_agent_based_plugins_dir

from cmk.gui.exceptions import MKUserError
from cmk.gui.utils.urls import werk_reference_url, WerkReference

from cmk.mkp_tool import PackageID
from cmk.update_config.plugins.pre_actions.utils import (
    AGENT_BASED_PLUGINS_PREACTION_SORT_INDEX,
    ConflictMode,
    continue_per_users_choice,
    get_installer_and_package_map,
    get_path_config,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction


class PreUpdateAgentBasedPlugins(PreUpdateAction):
    """Make sure no inactive agent based plug-ins are left over."""

    def _get_files(self) -> Sequence[Path]:
        try:
            return list(local_agent_based_plugins_dir.rglob("*.py"))
        except FileNotFoundError:
            return ()

    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        path_config = get_path_config()
        # In this case we have no mkp plugins available so bail out early
        if path_config is None:
            return
        _installer, package_map = get_installer_and_package_map(path_config)
        inactive_files = self._get_files()
        if inactive_files:
            for path in inactive_files:
                package_id = package_map.get(path.resolve())
                logger.error(_error_message_obsolete_file(path, package_id))
            logger.error(
                "Found obsolete files. These files are disabled by updating to the new version."
            )
            logger.error("See: %s\n", werk_reference_url(WerkReference.DECOMMISSION_V1_API))
            if not _continue_per_users_choice(conflict_mode):
                raise MKUserError(None, "decommissioned files")


def _continue_per_users_choice(conflict_mode: ConflictMode) -> bool:
    return continue_per_users_choice(
        conflict_mode,
        "You can abort the update process (A) and remove the file(s) or continue the update (c).\n\n"
        "Abort the update process? [A/c] \n",
    )


def _error_message_obsolete_file(path: Path, package_id: PackageID | None) -> str:
    hint = "" if package_id is None else f"of package {package_id.name} [{package_id.version}] "
    return f"Obsolete file: '{path}' {hint}"


pre_update_action_registry.register(
    PreUpdateAgentBasedPlugins(
        name="agent_based_plugins",
        title="Agent based plugins",
        sort_index=AGENT_BASED_PLUGINS_PREACTION_SORT_INDEX,
    )
)

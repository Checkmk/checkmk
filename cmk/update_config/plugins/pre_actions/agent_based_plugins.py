#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from logging import Logger
from pathlib import Path
from typing import override

from cmk.gui.exceptions import MKUserError
from cmk.gui.utils.urls import werk_reference_url, WerkReference
from cmk.mkp_tool import Manifest, PackageID
from cmk.update_config.plugins.pre_actions.utils import (
    AGENT_BASED_PLUGINS_PREACTION_SORT_INDEX,
    ConflictMode,
    continue_per_users_choice,
    disable_incomp_mkp,
    get_installer_and_package_map,
    get_path_config,
    is_applicable_mkp,
    PACKAGE_STORE,
    Resume,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction
from cmk.utils.paths import local_agent_based_plugins_dir


class PreUpdateAgentBasedPlugins(PreUpdateAction):
    """Make sure no inactive agent based plug-ins are left over."""

    def _get_files(self) -> Sequence[Path]:
        try:
            return list(local_agent_based_plugins_dir.rglob("*.py"))
        except FileNotFoundError:
            return ()

    @override
    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        path_config = get_path_config()
        # In this case we have no mkp plugins available so bail out early
        if path_config is None:
            return
        installer, package_map = get_installer_and_package_map(path_config)
        # group the local_agent_based_plugins_dir files by package
        grouped_files: dict[PackageID, list[Path]] = {}
        manifests: dict[PackageID, Manifest] = {}
        inactive_files_not_in_package = []
        for path in self._get_files():
            if (manifest := package_map.get(path.resolve())) is not None:
                grouped_files.setdefault(manifest.id, []).append(path)
                manifests[manifest.id] = manifest
            else:
                inactive_files_not_in_package.append(path)

        if inactive_files_not_in_package:
            _log_error_message_obsolete_files(logger, inactive_files_not_in_package)
            logger.error(
                "The above file(s) are not associated with any MKP and can thus not be removed automatically. "
                "You must manually remove them in order to suppress future warnings."
            )
            if _continue_per_users_choice(conflict_mode).is_abort():
                raise MKUserError(None, "decommissioned file(s)")

        for package_id, paths in grouped_files.items():
            if not is_applicable_mkp(manifests[package_id]):
                logger.info(
                    "[%s %s]: Ignoring problems (MKP will be disabled on target version)",
                    package_id.name,
                    package_id.version,
                )
                continue

            _log_error_message_obsolete_files(logger, paths)
            logger.error(
                f"The above file(s) are part of the extension package {package_id.name} {package_id.version}."
            )
            if disable_incomp_mkp(conflict_mode, package_id, installer, PACKAGE_STORE, path_config):
                continue
            raise MKUserError(None, "incompatible extension package")


def _continue_per_users_choice(conflict_mode: ConflictMode) -> Resume:
    match conflict_mode:
        case ConflictMode.FORCE:
            return Resume.UPDATE
        case ConflictMode.ABORT:
            return Resume.ABORT
        case ConflictMode.INSTALL | ConflictMode.KEEP_OLD:
            return Resume.ABORT
        case ConflictMode.ASK:
            return continue_per_users_choice(
                "You can abort the update process (A) or continue the update (c).\n"
                "Abort the update process? [A/c] \n",
            )


def _log_error_message_obsolete_files(logger: Logger, paths: Sequence[Path]) -> None:
    for path in paths:
        logger.error(f"Obsolete file: '{path}'")
    logger.error(
        "The file(s) residing in `local/lib/check_mk/plugins/agent_based` will no longer be loaded in Checkmk 2.4. "
    )
    logger.error("See: %s", werk_reference_url(WerkReference.DECOMMISSION_V1_API))


pre_update_action_registry.register(
    PreUpdateAgentBasedPlugins(
        name="agent_based_plugins",
        title="Agent based plugins",
        sort_index=AGENT_BASED_PLUGINS_PREACTION_SORT_INDEX,
    )
)

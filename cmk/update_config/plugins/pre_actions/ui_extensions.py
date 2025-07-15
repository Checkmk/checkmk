#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from logging import Logger
from pathlib import Path
from typing import override

from cmk.gui import main_modules
from cmk.gui.exceptions import MKUserError
from cmk.gui.utils import get_failed_plugins, remove_failed_plugin

from cmk.mkp_tool import Manifest, PackageID
from cmk.update_config.plugins.pre_actions.utils import (
    ConflictMode,
    continue_per_users_choice,
    disable_incomp_mkp,
    error_message_incomp_local_file,
    error_message_incomp_package,
    get_installer_and_package_map,
    get_path_config,
    GUI_PLUGINS_PREACTION_SORT_INDEX,
    is_applicable_mkp,
    PACKAGE_STORE,
    Resume,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction


def _get_package_manifest(package_map: Mapping[Path, Manifest], rel_path: str) -> Manifest | None:
    # What a knightmare, somebody please help.
    for path, package in package_map.items():
        if str(path).endswith(rel_path):
            return package
    return None


class PreUpdateUIExtensions(PreUpdateAction):
    """Load all web plugins before the real update happens"""

    @override
    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        main_modules.load_plugins()
        path_config = get_path_config()
        # no ui stuff to update
        if path_config is None:
            return
        installer, package_map = get_installer_and_package_map(path_config)
        dealt_with_packages: set[PackageID] = set()

        for path, _gui_part, _module_name, error in get_failed_plugins():
            manifest = _get_package_manifest(package_map, str(path))
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

            logger.error(error_message_incomp_package(path, manifest.id, error))
            if disable_incomp_mkp(
                conflict_mode, manifest.id, installer, PACKAGE_STORE, path_config
            ):
                dealt_with_packages.add(manifest.id)
                remove_failed_plugin(path)
                continue

            raise MKUserError(None, "incompatible extension package")


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
    PreUpdateUIExtensions(
        name="ui_extensions",
        title="UI extensions",
        sort_index=GUI_PLUGINS_PREACTION_SORT_INDEX,
    )
)

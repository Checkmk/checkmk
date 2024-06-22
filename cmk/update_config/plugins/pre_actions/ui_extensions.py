#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from logging import Logger
from pathlib import Path

from cmk.utils.exceptions import MKGeneralException

from cmk.gui import main_modules
from cmk.gui.exceptions import MKUserError
from cmk.gui.graphing import parse_perfometer, perfometer_info
from cmk.gui.utils import get_failed_plugins, remove_failed_plugin

from cmk.mkp_tool import PackageID
from cmk.update_config.plugins.pre_actions.utils import (
    ConflictMode,
    continue_on_incomp_local_file,
    disable_incomp_mkp,
    error_message_incomp_local_file,
    get_installer_and_package_map,
    get_path_config,
    GUI_PLUGINS_PREACTION_SORT_INDEX,
    PACKAGE_STORE,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction


def _get_package_id(package_map: Mapping[Path, PackageID], rel_path: str) -> PackageID | None:
    # What a knightmare, somebody please help.
    for path, package in package_map.items():
        if str(path).endswith(rel_path):
            return package
    return None


class PreUpdateUIExtensions(PreUpdateAction):
    """Load all web plugins before the real update happens"""

    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        main_modules.load_plugins()
        path_config = get_path_config()
        package_store = PACKAGE_STORE
        installer, package_map = get_installer_and_package_map(path_config)
        disabled_packages: set[PackageID] = set()
        for path, _gui_part, module_name, error in get_failed_plugins():
            package_id = _get_package_id(package_map, str(path))
            # unpackaged files
            if package_id is None:
                logger.error(error_message_incomp_local_file(path, error))
                if continue_on_incomp_local_file(conflict_mode):
                    continue
                raise MKUserError(None, "incompatible local file")

            if package_id in disabled_packages:
                continue  # already dealt with

            if disable_incomp_mkp(
                logger,
                conflict_mode,
                module_name,
                error,
                package_id,
                installer,
                package_store,
                path_config,
                path,
            ):
                disabled_packages.add(package_id)
                remove_failed_plugin(path)
                continue

            raise MKUserError(None, "incompatible extension package")

        for perfometer in perfometer_info:
            try:
                parse_perfometer(perfometer)
            except MKGeneralException as e:
                print(e)


pre_update_action_registry.register(
    PreUpdateUIExtensions(
        name="ui_extensions",
        title="UI extensions",
        sort_index=GUI_PLUGINS_PREACTION_SORT_INDEX,
    )
)

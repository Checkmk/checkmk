#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.packaging import PackageID

from cmk.gui import main_modules
from cmk.gui.exceptions import MKUserError
from cmk.gui.utils import get_failed_plugins, remove_failed_plugin

from cmk.update_config.plugins.pre_actions.utils import (
    ConflictMode,
    continue_on_incomp_local_file,
    disable_incomp_mkp,
    get_installer_and_package_map,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction


class PreUpdateUIExtensions(PreUpdateAction):
    """Load all web plugins before the real update happens"""

    def __call__(self, conflict_mode: ConflictMode) -> None:
        main_modules.load_plugins()
        installer, package_map = get_installer_and_package_map()
        disabled_packages: set[PackageID] = set()
        for path, _gui_part, module_name, error in get_failed_plugins():

            package_id = package_map.get(path.resolve())
            # unpackaged files
            if package_id is None:
                if continue_on_incomp_local_file(
                    conflict_mode,
                    module_name,
                    error,
                ):
                    continue
                raise MKUserError(None, "incompatible local file")

            if package_id in disabled_packages:
                continue  # already dealt with

            if disable_incomp_mkp(
                conflict_mode,
                module_name,
                error,
                package_id,
                installer,
            ):
                disabled_packages.add(package_id)
                remove_failed_plugin(path)
                continue

            raise MKUserError(None, "incompatible extension package")


pre_update_action_registry.register(
    PreUpdateUIExtensions(
        name="ui_extensions",
        title="UI extensions",
        sort_index=20,
    )
)

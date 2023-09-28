#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback
from pathlib import Path

from cmk.utils.packaging import PackageID
from cmk.utils.plugin_loader import load_plugins_with_exceptions

from cmk.gui.exceptions import MKUserError

from cmk.update_config.plugins.pre_actions.utils import (
    ConflictMode,
    continue_on_incomp_local_file,
    disable_incomp_mkp,
    get_installer_and_package_map,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction


class PreUpdateAgentBasedPlugins(PreUpdateAction):
    """Load all agent based plugins before the real update happens"""

    def __call__(self, conflict_mode: ConflictMode) -> None:
        installer, package_map = get_installer_and_package_map()
        disabled_packages: set[PackageID] = set()
        for module_name, error in load_plugins_with_exceptions("cmk.base.plugins.agent_based"):
            path = Path(traceback.extract_tb(error.__traceback__)[-1].filename)
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
                continue

            raise MKUserError(None, "incompatible local file")


pre_update_action_registry.register(
    PreUpdateAgentBasedPlugins(
        name="agent_based_plugins",
        title="Agent based plugins",
        sort_index=30,
    )
)

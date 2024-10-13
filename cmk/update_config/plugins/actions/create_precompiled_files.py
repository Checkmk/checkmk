#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from logging import Logger

from cmk.gui.watolib.hosts_and_folders import folder_tree

from cmk.update_config.registry import update_action_registry, UpdateAction


class CreatePrecompiledFiles(UpdateAction):
    """*.pkl files are version specific and generated from .mk files
    to improve the read performance.

    Create all precompiled files for better performance.
    """

    def __call__(self, _logger: Logger) -> None:
        for folder in folder_tree().root_folder().subfolders_recursively():
            folder.save()


update_action_registry.register(
    CreatePrecompiledFiles(
        name="create_precompiled_files",
        title="Create precompiled host and folder files",
        sort_index=5,
    )
)

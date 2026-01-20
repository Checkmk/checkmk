#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

import cmk.utils.paths
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.lib.remove_lib_check_mk_link import convert_manifests
from cmk.update_config.registry import update_action_registry, UpdateAction


class FixInstalledLibFiles(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        convert_manifests(cmk.utils.paths.installed_packages_dir, logger, dry_run=False)


update_action_registry.register(
    FixInstalledLibFiles(
        name="fix_installed_lib_files",
        title="Fix installed MKPs with files in local/lib/check_mk",
        sort_index=100,  # don't care
        expiry_version=ExpiryVersion.CMK_300,
    )
)

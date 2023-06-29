#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.utils.paths import check_mk_config_dir

from cmk.update_config.plugins.pre_actions.utils import ConflictMode
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction


class PreUpdateCleanupPrecompiledFiles(PreUpdateAction):
    """*.pkl files are version specific and generated from .mk files
    to improve the read performance.

    Cleanup the files of the previous version to make incompatible files not break the update
    procedure.
    """

    def __call__(self, _conflict_mode: ConflictMode) -> None:
        for p in Path(check_mk_config_dir, "wato").glob("**/*.pkl"):
            p.unlink(missing_ok=True)


pre_update_action_registry.register(
    PreUpdateCleanupPrecompiledFiles(
        name="cleanup_precompiled_files",
        title="Cleanup precompiled host and folder files",
        sort_index=5,
    )
)

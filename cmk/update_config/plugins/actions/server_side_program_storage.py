#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import Final, override

import cmk.utils.paths
from cmk.update_config.internal import ExpiryVersion, UpdateAction
from cmk.update_config.registry import update_action_registry

# Keep in sync with omd/packages/omd/skel/.profile
STORAGE_BASE_PATH: Final = cmk.utils.paths.var_dir / "server_side_program_storage"
# Keep in sync with cmk.server_side_programs.v1._storage
_STORAGE_NAMESPACE: Final = "storage"
# URL quoting never produces "%st", so this cannot be the name of a stored key.
_STAGING_NAME: Final = "%storage"


class MigrateServerSideProgramStorage(UpdateAction):
    """
    Move the values of `cmk.server_side_programs.v1.Storage` into their own namespace.

    Up to Checkmk 2.5 they were kept in <base>/<host>/<ident>/<key>, now they are kept
    in <base>/<host>/<ident>/storage/<key>, apart from those of `ObfuscatedStorage`.
    """

    @override
    def __call__(self, logger: Logger, *, debug: bool) -> None:
        self.migrate(STORAGE_BASE_PATH)

    @staticmethod
    def migrate(base_path: Path) -> None:
        for program_dir in base_path.glob("*/*"):
            if program_dir.is_dir():
                _migrate_program_dir(program_dir)


def _migrate_program_dir(program_dir: Path) -> None:
    staging = program_dir / _STAGING_NAME
    legacy_files = [p for p in program_dir.iterdir() if p.is_file()]
    if not legacy_files and not staging.is_dir():
        return

    # Move all files away first: one of them may be the key "storage".
    staging.mkdir(exist_ok=True)
    for legacy_file in legacy_files:
        legacy_file.rename(staging / legacy_file.name)

    target = program_dir / _STORAGE_NAMESPACE
    if not target.exists():
        staging.rename(target)
        return
    for staged_file in staging.iterdir():
        staged_file.rename(target / staged_file.name)
    staging.rmdir()


update_action_registry.register(
    MigrateServerSideProgramStorage(
        name="migrate_server_side_program_storage",
        title="Server-side programs: Move stored values to their own namespace",
        sort_index=101,  # no ordering constraints
        expiry_version=ExpiryVersion.CMK_310,
    )
)

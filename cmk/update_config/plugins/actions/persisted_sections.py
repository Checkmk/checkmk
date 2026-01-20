#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import shutil
from logging import Logger
from pathlib import Path
from typing import override

from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.paths import var_dir


class MigratePersistedSections(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        move_persisted_sections(var_dir)


def move_persisted_sections(var_dir: Path) -> None:
    old_persisted_dir = var_dir / "persisted"
    new_persisted_dir = var_dir / "persisted_sections/agent"

    if new_persisted_dir.exists():
        return

    new_persisted_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(old_persisted_dir, new_persisted_dir)
    except FileNotFoundError:
        # If the old directory does not exist, we have nothing to migrate.
        return


update_action_registry.register(
    MigratePersistedSections(
        name="persisted_sections",
        title="Migrate Persisted Sections",
        sort_index=99,  # don't care.
        expiry_version=ExpiryVersion.CMK_300,
    )
)

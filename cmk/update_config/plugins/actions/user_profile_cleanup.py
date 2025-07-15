#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from shutil import rmtree
from typing import override

from cmk.utils.paths import var_dir

from cmk.update_config.registry import update_action_registry, UpdateAction


class RemoveLeftoversUserProfileCleanup(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        (var_dir / "wato/last_user_profile_cleanup.mk").unlink(missing_ok=True)
        rmtree(var_dir / "background_jobs/user_profile_cleanup", ignore_errors=True)


update_action_registry.register(
    RemoveLeftoversUserProfileCleanup(
        name="user_profile_cleanup",
        title="Remove leftovers of user profile cleanup background job",
        sort_index=42,
    )
)

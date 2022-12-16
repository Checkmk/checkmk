#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.gui.backup import Config, site_config_path

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateBackupConfig(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        # Previous versions could set timeofday entries to None (CMK-7241). Clean this up for
        # compatibility.
        backup_config = Config(site_config_path()).load()
        for job_config in backup_config["jobs"].values():
            schedule = job_config.get("schedule", {})
            if schedule and "timeofday" in schedule:
                job_config["schedule"]["timeofday"] = [
                    e for e in schedule["timeofday"] if e is not None
                ]
        Config(site_config_path()).save(backup_config)


update_action_registry.register(
    UpdateBackupConfig(
        name="update_backup_config",
        title="Update backup config",
        sort_index=110,
    )
)

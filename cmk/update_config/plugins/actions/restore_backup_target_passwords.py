#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Undo the migration of the backup target secrets applied by the 2.5 ``Password`` FormSpec.

Only targets that still hold a FormSpec-shaped secret are touched, and only the site config
(``backup.mk``); the appliance-owned ``/etc/cma/backup.conf`` is never modified.
"""

from collections.abc import Mapping
from logging import Logger
from typing import override

from cmk.backup.gui.formspec_adapter import FormspecAdapter
from cmk.backup.utils.config import Config
from cmk.gui.form_specs import is_formspec_password
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.log import VERBOSE


def _has_formspec_password(value: object) -> bool:
    if is_formspec_password(value):
        return True
    match value:
        case Mapping():
            return any(_has_formspec_password(item) for item in value.values())
        case tuple() | list():
            return any(_has_formspec_password(item) for item in value)
        case _:
            return False


class RestoreBackupTargetPasswords(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        config = Config.load()

        restored = []
        for target_id, target_config in config.site.targets.items():
            if not _has_formspec_password(target_config):
                continue
            config.site.targets[target_id] = FormspecAdapter.from_form_spec(target_config)
            restored.append(target_id)

        if restored:
            config.save()
            logger.log(VERBOSE, "Fixed backup target secrets format for: %s", ", ".join(restored))


update_action_registry.register(
    RestoreBackupTargetPasswords(
        name="restore_backup_target_passwords",
        title="Fix backup target secrets format",
        sort_index=100,
        expiry_version=ExpiryVersion.CMK_310,
    )
)

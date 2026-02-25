#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import override

from cmk.ccc.store import DimSerializer, ObjectStore
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.paths import var_dir


class MigrateSigningKeyStates(UpdateAction):
    """The agent bakery keeps a cron job "execute_signing_key_validation_job" that alerts users
    when signing keys are about to expire. Before CMK-17514 the keys were int, now they are str-
    based (KeyId). Old int keys would cause dict lookups to miss in the expiry notification cronjob,
    silently skipping notifications. Convert any remaining int keys to str."""

    @override
    def __call__(self, logger: Logger) -> None:
        migrate_signing_key_states(var_dir / "wato" / "signing_key_states.mk")


def migrate_signing_key_states(state_file_path: Path) -> None:
    if not state_file_path.exists():
        return

    store = ObjectStore(state_file_path, serializer=DimSerializer())
    with store.locked():
        data = store.read_obj(default={})
        if not data:
            return
        migrated = {str(k): v for k, v in data.items()}
        if data != migrated:
            store.write_obj(migrated)


update_action_registry.register(
    MigrateSigningKeyStates(
        name="migrate_signing_key_states",
        title="Migrate bakery signing key state file keys from int to str",
        sort_index=100,  # don't care
        expiry_version=ExpiryVersion.CMK_260,
    )
)

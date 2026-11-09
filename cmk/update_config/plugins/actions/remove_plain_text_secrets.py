#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import Final, override

from cmk.update_config.internal import ExpiryVersion, UpdateAction
from cmk.update_config.plugins.actions.server_side_program_storage import STORAGE_BASE_PATH
from cmk.update_config.registry import update_action_registry

# (program identifier, key) of the secrets that server-side programs kept in a
# `Storage` up to Checkmk 2.5. They are now kept in an `ObfuscatedStorage`.
_PLAIN_TEXT_SECRETS: Final = (("veeam", "token"),)


class RemovePlainTextSecrets(UpdateAction):
    """
    Remove secrets that server-side programs stored in plain text up to Checkmk 2.5.

    The programs now keep them obfuscated, and recreate them if they are missing.
    """

    @override
    def __call__(self, logger: Logger, *, debug: bool) -> None:
        self.remove(STORAGE_BASE_PATH)

    @staticmethod
    def remove(base_path: Path) -> None:
        for ident, key in _PLAIN_TEXT_SECRETS:
            # <host>/<ident>/<namespace of Storage>/<key>
            for path in base_path.glob(f"*/{ident}/storage/{key}"):
                path.unlink(missing_ok=True)


update_action_registry.register(
    RemovePlainTextSecrets(
        name="remove_plain_text_server_side_program_secrets",
        title="Server-side programs: Remove secrets stored in plain text",
        sort_index=102,  # after migrate_server_side_program_storage
        expiry_version=ExpiryVersion.CMK_310,
    )
)

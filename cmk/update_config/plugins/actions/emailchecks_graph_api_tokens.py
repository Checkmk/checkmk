#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import Final, override
from urllib.parse import unquote

from cryptography.exceptions import InvalidTag

from cmk.password_store.v1 import get_store_secret, Obfuscator, PasswordStore, Secret
from cmk.server_side_programs.v1 import ObfuscatedStorage
from cmk.update_config.internal import ExpiryVersion, UpdateAction
from cmk.update_config.plugins.actions.server_side_program_storage import STORAGE_BASE_PATH
from cmk.update_config.registry import update_action_registry

# Keep in sync with cmk.plugins.emailchecks.lib.connections
_IDENT: Final = "graph_api_emailchecks"
# Where Checkmk 2.5 kept the files, after `MigrateServerSideProgramStorage` moved them.
_LEGACY_TOKEN_STORE: Final = "storage/stored_tokens"
_LEGACY_CREATED_MARKER: Final = "storage/created"


class MigrateGraphApiTokens(UpdateAction):
    """
    Move the tokens of the Graph API email connections into an `ObfuscatedStorage`.

    Up to Checkmk 2.5 they were kept in a password store file.
    Tokens that cannot be read are dropped, the connection then starts over with
    the configured initial tokens.
    """

    @override
    def __call__(self, logger: Logger, *, debug: bool) -> None:
        self.migrate(STORAGE_BASE_PATH)

    @staticmethod
    def migrate(base_path: Path) -> None:
        for program_dir in base_path.glob(f"*/{_IDENT}"):
            host = unquote(program_dir.parent.name)
            if (legacy_store := program_dir / _LEGACY_TOKEN_STORE).exists():
                _migrate_tokens(host, legacy_store)
            (program_dir / _LEGACY_CREATED_MARKER).unlink(missing_ok=True)


def _migrate_tokens(host: str, legacy_store: Path) -> None:
    secrets = ObfuscatedStorage(_IDENT, host, Obfuscator())
    for token_id, token in _read_legacy_tokens(legacy_store).items():
        if token_id in ("access_token", "refresh_token"):
            secrets.write(token_id, token)
    legacy_store.unlink()


def _read_legacy_tokens(legacy_store: Path) -> dict[str, Secret[str]]:
    try:
        return {**PasswordStore(get_store_secret()).load_bytes(legacy_store.read_bytes())}
    except InvalidTag, ValueError:
        return {}


update_action_registry.register(
    MigrateGraphApiTokens(
        name="migrate_emailchecks_graph_api_tokens",
        title="Email checks: Move Graph API tokens to obfuscated storage",
        sort_index=102,  # after migrate_server_side_program_storage
        expiry_version=ExpiryVersion.CMK_310,
    )
)

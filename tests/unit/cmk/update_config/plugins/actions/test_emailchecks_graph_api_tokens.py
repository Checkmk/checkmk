#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.password_store.v1 import Obfuscator, PasswordStore, Secret
from cmk.server_side_programs.v1 import ObfuscatedStorage
from cmk.update_config.plugins.actions.emailchecks_graph_api_tokens import MigrateGraphApiTokens

_PASSWORD_STORE_KEY = Secret(b"a" * 32)
_IDENT = "graph_api_emailchecks"
_HOST = "my host"  # quoted on disk


@pytest.fixture(name="base_path")
def fixture_base_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    key_file = tmp_path / "password_store.secret"
    key_file.write_bytes(_PASSWORD_STORE_KEY.reveal())
    monkeypatch.setenv("PASSWORD_STORE_SECRET_FILE", str(key_file))
    base_path = tmp_path / "storage"
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(base_path))
    return base_path


def _legacy_dir(base_path: Path) -> Path:
    # where Checkmk 2.5 kept the files, after the storage namespaces were introduced
    legacy_dir = base_path / "my%20host" / _IDENT / "storage"
    legacy_dir.mkdir(parents=True)
    return legacy_dir


def _secrets() -> ObfuscatedStorage[Secret[str]]:
    return ObfuscatedStorage(_IDENT, _HOST, Obfuscator())


def test_legacy_tokens_are_moved_to_obfuscated_storage(base_path: Path) -> None:
    (_legacy_dir(base_path) / "stored_tokens").write_bytes(
        PasswordStore(_PASSWORD_STORE_KEY).dump_bytes(
            {"access_token": Secret("old access"), "refresh_token": Secret("old refresh")}
        )
    )

    MigrateGraphApiTokens.migrate(base_path)

    secrets = _secrets()
    assert (secrets.read("access_token", None), secrets.read("refresh_token", None)) == (
        Secret("old access"),
        Secret("old refresh"),
    )


def test_unreadable_legacy_tokens_are_dropped(base_path: Path) -> None:
    (_legacy_dir(base_path) / "stored_tokens").write_bytes(b"\x00" * 100)

    MigrateGraphApiTokens.migrate(base_path)

    assert _secrets().read("refresh_token", None) is None


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b"\x00" * 100, id="unreadable"),
        pytest.param(PasswordStore(_PASSWORD_STORE_KEY).dump_bytes({}), id="readable"),
    ],
)
def test_legacy_files_are_removed(base_path: Path, content: bytes) -> None:
    legacy_dir = _legacy_dir(base_path)
    (legacy_dir / "stored_tokens").write_bytes(content)
    (legacy_dir / "created").write_text("true")

    MigrateGraphApiTokens.migrate(base_path)

    assert not list(legacy_dir.iterdir())

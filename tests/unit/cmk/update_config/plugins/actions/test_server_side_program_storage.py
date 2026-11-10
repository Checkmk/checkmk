#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.server_side_programs.v1 import ObfuscatedStorage, Storage
from cmk.update_config.plugins.actions.server_side_program_storage import (
    MigrateServerSideProgramStorage,
)

_HOST = "my_host"
_IDENT = "my_agent"


class _PlainObfuscator:
    def obfuscate(self, value: str, /) -> bytes:
        return value.encode()

    def deobfuscate(self, raw: bytes, /) -> str:
        return raw.decode()


@pytest.fixture(name="base_path")
def fixture_base_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path))
    return tmp_path


def _write_legacy(base_path: Path, key: str, content: str) -> None:
    program_dir = base_path / _HOST / _IDENT
    program_dir.mkdir(parents=True, exist_ok=True)
    (program_dir / key).write_text(content)


def test_legacy_values_are_readable_after_migration(base_path: Path) -> None:
    _write_legacy(base_path, "plain", "value of plain")
    _write_legacy(base_path, "storage", "value of storage")
    _write_legacy(base_path, "obfuscated_storage", "value of obfuscated_storage")

    MigrateServerSideProgramStorage.migrate(base_path)

    storage = Storage(_IDENT, _HOST)
    assert {key: storage.read(key, None) for key in ("plain", "storage", "obfuscated_storage")} == {
        "plain": "value of plain",
        "storage": "value of storage",
        "obfuscated_storage": "value of obfuscated_storage",
    }


def test_migrated_legacy_values_are_not_visible_to_obfuscated_storage(base_path: Path) -> None:
    _write_legacy(base_path, "obfuscated_storage", "value")

    MigrateServerSideProgramStorage.migrate(base_path)

    assert (
        ObfuscatedStorage(_IDENT, _HOST, _PlainObfuscator()).read("obfuscated_storage", None)
        is None
    )


def test_migrating_twice_keeps_values(base_path: Path) -> None:
    _write_legacy(base_path, "storage", "value")

    MigrateServerSideProgramStorage.migrate(base_path)
    MigrateServerSideProgramStorage.migrate(base_path)

    assert Storage(_IDENT, _HOST).read("storage", None) == "value"


def test_interrupted_migration_is_completed(base_path: Path) -> None:
    staging = base_path / _HOST / _IDENT / "%storage"
    staging.mkdir(parents=True)
    (staging / "moved").write_text("moved value")
    _write_legacy(base_path, "not_moved", "not moved value")

    MigrateServerSideProgramStorage.migrate(base_path)

    storage = Storage(_IDENT, _HOST)
    assert (storage.read("moved", None), storage.read("not_moved", None)) == (
        "moved value",
        "not moved value",
    )

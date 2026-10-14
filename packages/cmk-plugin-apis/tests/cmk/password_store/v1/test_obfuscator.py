#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.password_store.v1 import Obfuscator, PasswordStoreError, Secret
from cmk.server_side_programs.v1 import ObfuscatedStorage


@pytest.fixture(name="key_file")
def fixture_key_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    key_file = tmp_path / "password_store.secret"
    key_file.write_bytes(b"a" * 32)
    monkeypatch.setenv("PASSWORD_STORE_SECRET_FILE", str(key_file))
    return key_file


@pytest.mark.usefixtures("key_file")
def test_roundtrip() -> None:
    obfuscator = Obfuscator()
    assert obfuscator.deobfuscate(obfuscator.obfuscate(Secret("s3cr37!"))) == Secret("s3cr37!")


@pytest.mark.usefixtures("key_file")
def test_obfuscated_does_not_contain_plaintext() -> None:
    assert b"s3cr37!" not in Obfuscator().obfuscate(Secret("s3cr37!"))


@pytest.mark.usefixtures("key_file")
@pytest.mark.parametrize("raw", [b"", b"\x00\x00short", b"\x00" * 100])
def test_deobfuscate_garbage_raises_without_leaking_data(raw: bytes) -> None:
    with pytest.raises(ValueError) as exc_info:
        Obfuscator().deobfuscate(raw)
    assert repr(raw) not in str(exc_info.value)
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None


def test_deobfuscate_with_other_key_raises(key_file: Path) -> None:
    obfuscated = Obfuscator().obfuscate(Secret("s3cr37!"))
    key_file.write_bytes(b"b" * 32)
    with pytest.raises(ValueError):
        Obfuscator().deobfuscate(obfuscated)


def test_missing_key_raises_and_does_not_create_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    key_file = tmp_path / "password_store.secret"
    monkeypatch.setenv("PASSWORD_STORE_SECRET_FILE", str(key_file))
    with pytest.raises(PasswordStoreError):
        Obfuscator()
    assert not key_file.exists()


def _new_storage() -> ObfuscatedStorage[Secret[str]]:
    # The annotation makes mypy check that Obfuscator satisfies ObfuscatorP.
    storage: ObfuscatedStorage[Secret[str]] = ObfuscatedStorage(
        "test_agent", "test_host", Obfuscator()
    )
    return storage


@pytest.fixture(name="storage_path")
def fixture_storage_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path / "storage"))


@pytest.mark.usefixtures("key_file", "storage_path")
def test_secret_survives_obfuscated_storage() -> None:
    _new_storage().write("key", Secret("s3cr37!"))

    assert _new_storage().read("key", None) == Secret("s3cr37!")


@pytest.mark.usefixtures("storage_path")
def test_obfuscated_storage_returns_default_after_key_change(key_file: Path) -> None:
    _new_storage().write("key", Secret("s3cr37!"))
    key_file.write_bytes(b"b" * 32)

    assert _new_storage().read("key", None) is None

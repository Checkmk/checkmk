#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from pathlib import Path

import pytest

from cmk.server_side_programs.v1 import ObfuscatedStorage, Storage

TEST_AGENT = "test_agent"
TEST_HOST = "test_host"


class _ReversingObfuscator:
    def obfuscate(self, value: int, /) -> bytes:
        return str(value).encode()[::-1]

    def deobfuscate(self, raw: bytes, /) -> int:
        return int(raw[::-1].decode())  # raises ValueError for anything not an int


@pytest.fixture(name="storage")
def fixture_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ObfuscatedStorage[int]:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path))
    return ObfuscatedStorage(TEST_AGENT, TEST_HOST, _ReversingObfuscator())


def test_write_read(storage: ObfuscatedStorage[int]) -> None:
    storage.write("key", 123)
    assert storage.read("key", None) == 123


def test_write_stores_obfuscated_bytes(storage: ObfuscatedStorage[int], tmp_path: Path) -> None:
    storage.write("key", 123)
    assert [p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()] == [b"321"]


def test_write_overwrites_existing_key(storage: ObfuscatedStorage[int]) -> None:
    storage.write("key", 1)
    storage.write("key", 2)
    assert storage.read("key", None) == 2


def test_read_nonexistent_returns_default(storage: ObfuscatedStorage[int]) -> None:
    assert storage.read("does_not_exist", "default") == "default"


def test_read_undeobfuscatable_returns_default(
    storage: ObfuscatedStorage[int], tmp_path: Path
) -> None:
    storage.write("key", 123)
    (stored_file,) = (p for p in tmp_path.rglob("*") if p.is_file())
    stored_file.write_bytes(b"not a number")
    assert storage.read("key", "default") == "default"


def test_unset(storage: ObfuscatedStorage[int]) -> None:
    storage.write("key", 123)
    storage.unset("key")
    assert storage.read("key", None) is None


def test_write_key_too_long_after_quoting(storage: ObfuscatedStorage[int]) -> None:
    # 86 characters, but 258 after URL quoting ("/" -> "%2F")
    with pytest.raises(ValueError):
        storage.write("/" * 86, 1)


@pytest.mark.parametrize(
    "operation",
    [
        pytest.param(lambda s: s.write("key", 1), id="write"),
        pytest.param(lambda s: s.read("key", None), id="read"),
        pytest.param(lambda s: s.unset("key"), id="unset"),
    ],
)
def test_missing_storage_path_raises(
    monkeypatch: pytest.MonkeyPatch,
    operation: Callable[[ObfuscatedStorage[int]], object],
) -> None:
    monkeypatch.delenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", raising=False)
    storage = ObfuscatedStorage(TEST_AGENT, TEST_HOST, _ReversingObfuscator())

    with pytest.raises(RuntimeError):
        operation(storage)


def test_same_key_in_storage_and_obfuscated_storage_does_not_collide(
    storage: ObfuscatedStorage[int],
) -> None:
    plain = Storage(TEST_AGENT, TEST_HOST)

    storage.write("key", 123)
    plain.write("key", "plain value")

    assert (storage.read("key", None), plain.read("key", None)) == (123, "plain value")

#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.user import UserId

from cmk.gui.utils.htpasswd import Entries, Htpasswd

from cmk.crypto.password_hashing import PasswordHash


@pytest.fixture(name="htpasswd_file")
def fixture_htpasswd_file(tmp_path: Path) -> Path:
    """Write entries to a temp file and return the file path"""
    htpwd_file = tmp_path / "htpasswd"
    htpwd_file.write_text(
        r"""
automation:$2💖$12$Da58z4tHEIVsMKcR4JS9KO7jNCg9SARhV0F1lXJpTH/HBvIDRsDwK
cmkadmin:acdikmmn
cmkadmin:override!

mallory:injecting\nanother:user

$admin$:bäää
invalid lines should be ignored
inactive:!should be loaded
invalid🔥user:should be ignored
""",
        encoding="utf-8",
    )
    return htpwd_file


@pytest.fixture(name="users")
def fixture_users() -> Entries:
    return {
        # Htpasswd doesn't care if the hash is valid or even sensible
        UserId("non-unicode"): PasswordHash(""),
        UserId("abcä"): PasswordHash("bbbä"),
        UserId("$user"): PasswordHash("🙆🙅"),
    }


@pytest.fixture(name="no_users")
def fixture_no_users() -> list[UserId]:
    return [UserId("not-existant"), UserId("")]


@pytest.fixture(name="test_config")
def fixture_test_config(tmp_path: Path, users: Entries) -> Htpasswd:
    htpwd = Htpasswd(tmp_path / "htpasswd")
    htpwd.save_all(users)
    return htpwd


def test_load(htpasswd_file: Path) -> None:
    users = Htpasswd(htpasswd_file).load()

    assert len(users) == 5, "all valid users, including inactive, are loaded"
    assert users[UserId("cmkadmin")] == "override!", "last seen hash wins duplicates"
    assert users[UserId("mallory")] == "injecting\\nanother:user"


def test_save_all(htpasswd_file: Path, users: Entries) -> None:
    Htpasswd(htpasswd_file).save_all(users)
    content = htpasswd_file.read_text(encoding="utf-8")

    assert all(user in content for user in users)
    assert len(content.splitlines()) == len(users)
    assert "cmkadmin" not in content, "old file is written over"


def test_exists(test_config: Htpasswd, users: Entries, no_users: list[UserId]) -> None:
    for user in users:
        assert test_config.exists(user)

    for user in no_users:
        assert not test_config.exists(user)

    assert test_config.load() == users, "entries are unchanged"


def test_get_hash(test_config: Htpasswd, users: Entries, no_users: list[UserId]) -> None:
    for user in users:
        assert test_config.get_hash(user) == users[user]

    for user in no_users:
        assert test_config.get_hash(user) is None


@pytest.mark.parametrize(
    "user, password_hash",
    [
        ("new_user", "hash"),
        ("$nü$üser$", "!hash"),
        ("", ""),  # as long as UserId allows this...
    ],
)
def test_save_new_user(test_config: Htpasswd, user: str, password_hash: str) -> None:
    user_id = UserId(user)
    before = test_config.load()

    test_config.save(user_id, PasswordHash(password_hash))

    after = test_config.load()
    assert all(old_user in after for old_user in before)
    assert len(after) == len(before) + 1
    assert user_id in after


def test_save_override_existing_user(test_config: Htpasswd) -> None:
    before = test_config.load()

    # test_config fixture added this user with a different hash already
    test_config.save(UserId("$user"), PasswordHash("!now inactive"))

    after = test_config.load()
    assert all(old_user in after for old_user in before)
    assert len(after) == len(before)

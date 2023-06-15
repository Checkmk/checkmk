#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime

import pytest

from tests.unit.cmk.gui.test_userdb import _load_users_uncached

from cmk.utils.crypto.password_hashing import is_unsupported_legacy_hash, PasswordHash
from cmk.utils.user import UserId

from cmk.gui.userdb import save_users, Users, UserSpec

from cmk.update_config.plugins.actions.password_hashes import CheckPasswordHashes


@pytest.fixture(name="run_check")
def fixture_check_pw_hashes_action() -> CheckPasswordHashes:
    """Action to test as it's registered in the real world"""

    return CheckPasswordHashes(
        name="check_password_hashes",
        title="Check for incompatible password hashes",
        sort_index=100,
    )


@pytest.fixture(name="existing_users")
def fixture_userdb(with_user: tuple[UserId, str]) -> Users:
    """Users currently stored in the userdb. Needed so save_users won't remove the current user"""
    # 'with_user' is needed for the application context and initially filling the userdb

    existing = _load_users_uncached(lock=False)

    # ensure existing test users don't trigger the warning
    assert all(
        (pw := existing[user].get("password")) and not is_unsupported_legacy_hash(pw)
        for user in existing
    ), "Legacy password hash found in test user data"

    return existing


class _MockLogger:
    def __init__(self) -> None:
        self.warnings: list[str] = []

    def warning(self, msg: str) -> None:
        self.warnings.append(msg)


@pytest.mark.parametrize(
    "username,pw_hash,should_warn",
    [
        # these are no longer supported (the username indicates the hashing scheme):
        ("md5", "$apr1$EpPwa/X9$TB2UcQxmrSTJWQQcwHzJM/", True),
        ("crypt", "WsbFVbJdvDcpY", True),
        (
            "sha256crypt",
            "$5$rounds=1000$.J4mcfJGFGgWJA7R$bDhUCLMe2v1.L3oWclfsVYMyOhsS/6RmyzqFRyCgDi/",
            True,
        ),
        (
            "sha256crypt_no_rounds",
            "$5$H2kwlVdGl9PLMISm$RrQUaIqzFzHmW7SjvCRGV4LsHM2WBT4B0OaGm7TIFI9",
            True,
        ),
        # bcrypt (both possible identifiers) is fine:
        ("bcrypt_2b", "$2b$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa", False),
        ("bcrypt_2y", "$2y$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa", False),
        # locking does not change the result:
        (
            "sha256crypt_locked",
            "!$5$rounds=1000$.J4mcfJGFGgWJA7R$bDhUCLMe2v1.L3oWclfsVYMyOhsS/6RmyzqFRyCgDi/",
            True,
        ),
        (
            "bcrypt_locked",
            "!$2b$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa",
            False,
        ),
        # can't identify hash -- we didn't put that there, so we'll leave it alone:
        ("unrecognized", "foo", False),
    ],
)
def test_check_password_hashes(
    existing_users: Users,
    run_check: CheckPasswordHashes,
    username: str,
    pw_hash: str,
    should_warn: bool,
) -> None:
    test_user = {
        UserId(username): UserSpec({"connector": "htpasswd", "password": PasswordHash(pw_hash)})
    }

    # automation user with legacy hash that should not receive a warning
    automation_md5 = {
        UserId("automation_md5"): UserSpec(
            {
                "connector": "htpasswd",
                "password": PasswordHash("$apr1$EpPwa/X9$TB2UcQxmrSTJWQQcwHzJM/"),
                "automation_secret": "foo",
            }
        )
    }

    save_users(
        test_user | automation_md5 | existing_users,
        datetime.datetime.now(),
    )
    mock_logger = _MockLogger()

    run_check(mock_logger, {})  # type: ignore[arg-type]

    if should_warn:
        assert len(mock_logger.warnings) == 1
        assert username in mock_logger.warnings[0]
    else:
        assert len(mock_logger.warnings) == 0

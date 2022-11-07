#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import warnings
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from cmk.utils.crypto import Password, password_hashing
from cmk.utils.type_defs import UserId

import cmk.gui.plugins.userdb.htpasswd as htpasswd
from cmk.gui.exceptions import MKUserError


@pytest.fixture(name="htpasswd_file", autouse=True)
def htpasswd_file_fixture(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    htpasswd_file_path = tmp_path / "htpasswd"
    # HtpasswdUserConnector will use this path:
    monkeypatch.setattr("cmk.utils.paths.htpasswd_file", htpasswd_file_path)

    # all hashes below belong to the password "cmk"
    hashes = [
        # Pre 1.6 hashing formats (see cmk.gui.plugins.userdb.htpasswd for more details)
        "bärnd:$apr1$/FU.SwEZ$Ye0XG1Huf2j7Jws7KD.h2/",
        "cmkadmin:NEr3kqi287FQc",
        "harry:$1$478020$ldQUQ3RIwRYk5wjKfsWPD.",
        # A disabled user
        "locked:!NEr3kqi287FQc",
        # A >= 1.6 sha256 hashed password
        "sha256user:$5$rounds=1000$.L//WfAGgL3rOSs3$QXLgMhQIDaL2oDagb7kLd.jRbyKLG9wsikCfzAq/w01",
        "locked_sha256user:!$5$rounds=1000$.L//WfAGgL3rOSs3$QXLgMhQIDaL2oDagb7kLd.jRbyKLG9wsikCfzAq/w01",
        # A >= 2.1 bcrypt hashed password
        "bcrypt_user:$2b$04$IJJ8O2HLU5KEZL2ZbybonODhQ/0TPPgARwDhib74KFU5uRvyUupcO",
    ]
    htpasswd_file_path.write_text("\n".join(sorted(hashes)) + "\n", encoding="utf-8")

    return htpasswd_file_path


@pytest.mark.parametrize(
    "password",
    [
        "blä",
        "😀",
        "😀" * 18,
        "a" * 71,
    ],
)
def test_hash_password(password: str) -> None:
    # Suppress this warning from passlib code. We can not do anything about this and it clutters our
    # unit test log
    # tests/unit/cmk/gui/test_userdb_htpasswd_connector.py::test_hash_password
    # (...)/handlers/bcrypt.py:378: DeprecationWarning: NotImplemented should not be used in a boolean context
    # if not result:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        hashed_pw = htpasswd.hash_password(Password(password))
    password_hashing.verify(Password(password), hashed_pw)


def test_truncation_error() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        with pytest.raises(MKUserError):
            htpasswd.hash_password(Password("A" * 72 + "foo"))
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        with pytest.raises(MKUserError):
            htpasswd.hash_password(Password("😀" * 19))


@pytest.mark.parametrize(
    "user,expect_update",
    [
        ("bärnd", False),
        ("cmkadmin", False),
        ("harry", False),
        ("locked", False),
        ("sha256user", True),
        ("locked_sha256user", False),
        ("bcrypt_user", False),
    ],
)
def test_update_hashes(htpasswd_file: Path, user: UserId, expect_update: bool) -> None:
    password = Password("cmk")
    htpasswd_connector = htpasswd.HtpasswdUserConnector({})
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        htpasswd_connector.check_credentials(user, password)

    # Note: bcrypt $2b$ hashes are not "updated" to $2y$
    assert (
        f"{user}:$2y$" in htpasswd_file.read_text()
    ) == expect_update, "Only sha256-crypt hashes are updated"

    if not "locked" in user:
        assert (
            htpasswd_connector.check_credentials(user, password) == user
        ), "Password is still valid"


def test_update_long_password(htpasswd_file: Path) -> None:
    """This tests that passwords that were valid with sha256crypt but are not valid with bcrypt
    (specifically passwords longer than 72 bytes), are handled properly during hash migration.
    """
    htpasswd_connector = htpasswd.HtpasswdUserConnector({})
    usr = UserId("longcat")
    pw = 74 * "x"  # too long for bcrypt
    pw_hash = "$5$rounds=1000$FwEKt/q2WUEYYjOm$EhgODZbqGIl8LcdDtGYYjfFLECubBN.xNSavUiP5.UB"
    htpasswd_file.write_text(f"{usr}:{pw_hash}\n")

    assert (
        htpasswd_connector.check_credentials(usr, Password(pw)) == usr
    ), "Long passwords still work"
    assert (
        htpasswd_connector.check_credentials(usr, Password(pw[:72])) == usr
    ), "The password is now truncated"


def test_user_connector_verify_password() -> None:
    htpasswd_connector = htpasswd.HtpasswdUserConnector({})
    pw = Password("cmk")
    assert htpasswd_connector.check_credentials(UserId("cmkadmin"), pw) == "cmkadmin"
    assert htpasswd_connector.check_credentials(UserId("bärnd"), pw) == "bärnd"
    assert htpasswd_connector.check_credentials(UserId("sha256user"), pw) == "sha256user"
    assert htpasswd_connector.check_credentials(UserId("harry"), pw) == "harry"
    assert htpasswd_connector.check_credentials(UserId("bcrypt_user"), pw) == "bcrypt_user"
    assert htpasswd_connector.check_credentials(UserId("dingeling"), Password("aaa")) is None
    assert htpasswd_connector.check_credentials(UserId("locked"), Password("locked")) is False

    # Check no exception is raised, when setting a password > 72 chars a exception is raised...
    assert htpasswd_connector.check_credentials(UserId("bcrypt_user"), Password("A" * 100)) is False

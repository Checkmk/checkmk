#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

import cmk.utils.crypto.secrets as secrets
from cmk.utils.user import UserId


def test_create_secret_and_hmac(tmp_path: Path) -> None:
    """A secret can be instantiated and the HMAC comes out as expected"""

    my_secret_file = tmp_path / "mytest.secret"
    my_secret_file.write_bytes(b"my test secret")

    class MySecret(secrets._LocalSecret):
        path = my_secret_file

    secret = MySecret()

    assert secret.path == my_secret_file
    assert (
        secret.hmac("hello") == "3bc5a0f1f479929f6c6330bd2dabf2d78ed389ab329f2c0b0baadfb3a01dbeae"
    )


def test_empty_secrets_get_overwritten(tmp_path: Path) -> None:
    """Empty secret files get overwritten.

    Note that Secret would raise an error if you tried to create an empty secret.
    This test ensures that LocalSecret deals with empty files.
    """

    my_secret_file = tmp_path / "mytest.secret"
    my_secret_file.touch()

    class MySecret(secrets._LocalSecret):
        path = my_secret_file

    assert MySecret().secret


def test_automation_user_secret() -> None:
    aus = secrets.AutomationUserSecret(UserId("crypto_secrets_new_user"))

    assert not aus.exists()
    with pytest.raises(FileNotFoundError):
        aus.read()

    aus.path.parent.mkdir()  # profile dir of the test user
    aus.save(secret := "this is a test 🤡")

    assert aus.exists()
    assert aus.read() == secret

    assert not aus.check("")
    assert not aus.check("wrong")
    assert aus.check(secret)


def test_refusing_to_create_empty_secrets() -> None:
    """Refusing to create empty secrets"""

    with pytest.raises(ValueError):
        secrets.Secret(b"")

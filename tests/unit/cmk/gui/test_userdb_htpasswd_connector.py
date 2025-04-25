#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest import MonkeyPatch

from cmk.ccc.user import UserId

from cmk.gui.exceptions import MKUserError
from cmk.gui.userdb import CheckCredentialsResult, htpasswd

from cmk.crypto import password_hashing
from cmk.crypto.password import Password


@pytest.fixture(name="htpasswd_file", autouse=True)
def htpasswd_file_fixture(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    htpasswd_file_path = tmp_path / "htpasswd"
    # HtpasswdUserConnector will use this path:
    monkeypatch.setattr("cmk.utils.paths.htpasswd_file", htpasswd_file_path)

    hashes = [
        # all hashes below belong to the password "cmk"
        "$cmk@dmin$:$2y$04$XZECL0BqDf8Er3iygLfRBO7wwg8igYcI4K49Jtn8AnJMJaP2Lx/ki",
        "bärnd:$2y$04$71x8EVHr7c8FP8HJ/PWN7uM27SC0Z89waQCaiYovaiSAslb1sh2sO",
        "locked_bärnd:!$2y$04$71x8EVHr7c8FP8HJ/PWN7uM27SC0Z89waQCaiYovaiSAslb1sh2sO",
        # sha256_crypt hashes (of "cmk"), which are no longer supported
        "legacy_hash:$5$kNFothH2RmxLOgvZ$zYYzORO.TxsYwbWvdXdQURuNlO2yFBmEZaRk2QxT1dC",
        "locked_legacy_hash:!$5$kNFothH2RmxLOgvZ$zYYzORO.TxsYwbWvdXdQURuNlO2yFBmEZaRk2QxT1dC",
    ]

    htpasswd_file_path.write_text("\n".join(sorted(hashes)) + "\n", encoding="utf-8")

    return htpasswd_file_path


@pytest.mark.parametrize("password", ["blä", "😀", "😀" * 18, "a" * 71])
def test_hash_password(password: str) -> None:
    hashed_pw = htpasswd.hash_password(Password(password))
    password_hashing.verify(Password(password), hashed_pw)


def test_truncation_error() -> None:
    """Bcrypt doesn't allow passwords longer than 72 bytes"""

    with pytest.raises(MKUserError):
        htpasswd.hash_password(Password("A" * 72 + "foo"))

    with pytest.raises(MKUserError):
        htpasswd.hash_password(Password("😀" * 19))


@pytest.mark.parametrize(
    # uids/passwords correspond to users from the htpasswd_file_fixture
    "uid,password,expect",
    [
        # valid
        (UserId("$cmk@dmin$"), Password("cmk"), UserId("$cmk@dmin$")),
        (UserId("bärnd"), Password("cmk"), UserId("bärnd")),
        # wrong password
        (UserId("bärnd"), Password("foo"), False),
        # unsupported hash
        (UserId("legacy_hash"), Password("cmk"), False),
        # user not in htpasswd (potentially other connector)
        (UserId("unknown"), Password("cmk"), None),
        # check that PWs too long for bcrypt are handled gracefully and don't raise
        (UserId("bärnd"), Password("A" * 100), False),
    ],
)
def test_user_connector_verify_password(
    uid: UserId, password: Password, expect: CheckCredentialsResult
) -> None:
    assert (
        htpasswd.HtpasswdUserConnector(
            {
                "type": "htpasswd",
                "id": "htpasswd",
                "disabled": False,
            }
        ).check_credentials(uid, password)
        == expect
    )


@pytest.mark.parametrize(
    "uid,password",
    [
        (UserId("locked_bärnd"), Password("cmk")),
        (UserId("locked_legacy_hash"), Password("cmk")),
    ],
)
def test_user_connector_verify_password_locked_users(
    uid: UserId,
    password: Password,
) -> None:
    with pytest.raises(MKUserError, match="User is locked"):
        htpasswd.HtpasswdUserConnector(
            {
                "type": "htpasswd",
                "id": "htpasswd",
                "disabled": False,
            }
        ).check_credentials(uid, password)

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import cast

from cmk.ccc.user import UserId
from cmk.crypto.password_hashing import PasswordHash
from cmk.gui.type_defs import SessionInfo, TwoFactorCredentials, UserSpec
from cmk.gui.userdb import UserAttribute
from cmk.gui.userdb.user_attributes import ForceAuthUserUserAttribute
from cmk.gui.userdb.userdata import UserData, UserDataDiff


def _user(
    spec: Mapping[str, object],
    user_attributes: Sequence[tuple[str, UserAttribute]] = (),
) -> UserData:
    return UserData.from_userspec(
        UserId("happy"),
        cast(UserSpec, {"alias": "Happy Testuser", "roles": []} | dict(spec)),
        user_attributes,
    )


def test_diff_reports_only_changed_fields() -> None:
    before = _user({})
    after = _user({"email": "happy@example.com", "force_authuser": False})

    diff = UserDataDiff.between(before, after)

    assert diff.attribute_changes == (
        'Value of "email" changed from None to "happy@example.com".\n'
        'Attribute "force_authuser" with value False added.'
    )


def test_diff_reports_changed_secrets_without_revealing_them() -> None:
    before = _user({"password": PasswordHash("$2y$04$oldhash")})
    after = _user(
        {
            "password": PasswordHash("$2y$04$newhash"),
            "automation_secret": "automation-secret",
            "two_factor_credentials": TwoFactorCredentials(
                webauthn_credentials={},
                backup_codes=[PasswordHash("$2y$04$backupcode")],
                totp_credentials={},
            ),
        }
    )

    diff = UserDataDiff.between(before, after)

    assert diff.attribute_changes == ""
    assert diff.credentials_changed


def test_diff_ignores_internal_state() -> None:
    session = {"session": SessionInfo(session_id="session", started_at=0, last_activity=0)}
    before = _user({"session_info": session, "user_scheme_serial": 0})
    after = _user({"user_scheme_serial": 1})

    diff = UserDataDiff.between(before, after)

    assert diff.attribute_changes == ""
    assert not diff.credentials_changed


def test_diff_reports_builtin_attribute_once() -> None:
    # force_authuser is both an explicit UserData field and a registered user attribute
    attrs = [("force_authuser", ForceAuthUserUserAttribute())]
    before = _user({}, attrs)
    after = _user({"force_authuser": False}, attrs)

    diff = UserDataDiff.between(before, after)

    assert diff.attribute_changes == 'Attribute "force_authuser" with value False added.'

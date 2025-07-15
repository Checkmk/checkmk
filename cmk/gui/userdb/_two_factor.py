#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast

from cmk.ccc.user import UserId

from cmk.gui.type_defs import TwoFactorCredentials

from cmk.crypto import password_hashing
from cmk.crypto.password import Password

from .store import load_custom_attr, save_two_factor_credentials


def is_two_factor_login_enabled(user_id: UserId) -> bool:
    """Whether or not 2FA is enabled for the given user"""
    return bool(
        load_two_factor_credentials(user_id)["webauthn_credentials"]
        or load_two_factor_credentials(user_id)["totp_credentials"]
    )


def disable_two_factor_authentication(user_id: UserId) -> None:
    credentials = load_two_factor_credentials(user_id, lock=True)
    credentials["webauthn_credentials"].clear()
    credentials["totp_credentials"].clear()
    save_two_factor_credentials(user_id, credentials)


def load_two_factor_credentials(user_id: UserId, lock: bool = False) -> TwoFactorCredentials:
    cred = load_custom_attr(
        user_id=user_id, key="two_factor_credentials", parser=ast.literal_eval, lock=lock
    )
    return (
        TwoFactorCredentials(webauthn_credentials={}, backup_codes=[], totp_credentials={})
        if cred is None
        else cred
    )


def make_two_factor_backup_codes(
    *, rounds: int | None = None
) -> list[tuple[Password, password_hashing.PasswordHash]]:
    """Creates a set of new two factor backup codes

    The codes are returned in plain form for displaying and in hashed+salted form for storage
    """
    return [
        (password, password_hashing.hash_password(password))
        for password in (Password.random(10) for _ in range(10))
    ]


def is_two_factor_backup_code_valid(user_id: UserId, code: Password) -> bool:
    """Verifies whether or not the given backup code is valid and invalidates the code"""
    credentials = load_two_factor_credentials(user_id)
    matched_code = None

    for stored_code in credentials["backup_codes"]:
        try:
            password_hashing.verify(code, stored_code)
            matched_code = stored_code
            break
        except (password_hashing.PasswordInvalidError, ValueError):
            continue

    if matched_code is None:
        return False

    # Invalidate the just used code
    credentials = load_two_factor_credentials(user_id, lock=True)
    credentials["backup_codes"].remove(matched_code)
    save_two_factor_credentials(user_id, credentials)

    return True

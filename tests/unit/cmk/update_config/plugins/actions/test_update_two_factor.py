#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import mocklogger

from cmk.utils.crypto.password import PasswordHash
from cmk.utils.user import UserId

from cmk.gui.type_defs import TotpCredential, TwoFactorCredentials, WebAuthnCredential
from cmk.gui.userdb import load_two_factor_credentials
from cmk.gui.userdb.store import save_two_factor_credentials

from cmk.update_config.plugins.actions.update_two_factor import UpdateExistingTwoFactor


@pytest.fixture(name="run_check")
def fixture_check_pw_hashes_action() -> UpdateExistingTwoFactor:
    """Action to test as it's registered in the real world"""

    return UpdateExistingTwoFactor(
        name="update_two_factor",
        title="Update Existing Two Factor",
        sort_index=102,
        continue_on_failure=False,
    )


@pytest.fixture(name="user_id")
def fixture_user_id(with_user: tuple[UserId, str]) -> UserId:
    return with_user[0]


@pytest.fixture(name="with_missing_totp")
def test_save_two_factor_credentials_no_totp(user_id: UserId) -> None:
    credentials = TwoFactorCredentials(
        {
            "webauthn_credentials": {
                "id": WebAuthnCredential(
                    credential_id="id",
                    registered_at=1337,
                    alias="Steckding",
                    credential_data=b"whatever",
                ),
            },
            "backup_codes": [
                PasswordHash("asdr2ar2a2ra2rara2"),
                PasswordHash("dddddddddddddddddd"),
            ],
            "totp_credentials": {},
        }
    )
    # removing totp to simulate an older two factor file
    credentials.pop("totp_credentials")  # type: ignore[misc]
    save_two_factor_credentials(user_id, credentials)
    assert load_two_factor_credentials(user_id) == credentials


@pytest.fixture(name="with_totp")
def test_save_two_factor_credentials_with_totp(user_id: UserId) -> None:
    credentials = TwoFactorCredentials(
        {
            "webauthn_credentials": {
                "id": WebAuthnCredential(
                    credential_id="id",
                    registered_at=1337,
                    alias="Steckding",
                    credential_data=b"whatever",
                ),
            },
            "backup_codes": [
                PasswordHash("asdr2ar2a2ra2rara2"),
                PasswordHash("dddddddddddddddddd"),
            ],
            "totp_credentials": {
                "uuid": TotpCredential(
                    {
                        "credential_id": "uuid",
                        "secret": b"whatever",
                        "version": 1,
                        "registered_at": 1337,
                        "alias": "Steckding",
                    }
                ),
            },
        }
    )
    save_two_factor_credentials(user_id, credentials)
    assert load_two_factor_credentials(user_id) == credentials


def test_missing_totp_in_mfa_mk_file(
    with_missing_totp: None, run_check: UpdateExistingTwoFactor
) -> None:
    """User's two factor file is missing totp entry"""
    mock_logger = mocklogger.MockLogger()
    run_check(mock_logger, {})  # type: ignore[arg-type]

    assert len(mock_logger.messages) == 1
    assert "1 user(s) had their two factor" in mock_logger.messages[0]


def test_existing_totp_in_mfa_mk_file(with_totp: None, run_check: UpdateExistingTwoFactor) -> None:
    """User's two factor file is up to date"""
    mock_logger = mocklogger.MockLogger()
    run_check(mock_logger, {})  # type: ignore[arg-type]

    assert len(mock_logger.messages) == 0

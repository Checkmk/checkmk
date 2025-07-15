#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import patch

import pytest

from cmk.crypto.password import PasswordPolicy
from cmk.gui.exceptions import MKUserError
from cmk.gui.openapi.endpoints.user_config import _auth_options_to_internal_format


@patch("time.time", return_value=1234567890)
@patch("cmk.gui.userdb.htpasswd.hash_password", return_value="hashed_password")
def test_automation_secret(mock_hash: None, mock_time: None) -> None:
    result = _auth_options_to_internal_format(
        {"auth_type": "automation", "secret": "TNBJCkwane3$cfn0XLf6p6a"},
        PasswordPolicy(12, None),
    )

    expected = {
        "password": "hashed_password",
        "automation_secret": "TNBJCkwane3$cfn0XLf6p6a",
        "store_automation_secret": False,
        "is_automation_user": True,
        "last_pw_change": 1234567890,
    }
    assert result == expected


def test_enforce_password_change_only() -> None:
    result = _auth_options_to_internal_format(
        {"auth_type": "password", "enforce_password_change": True},
        PasswordPolicy(12, None),
    )

    expected = {"enforce_pw_change": True}
    assert result == expected


def test_empty_password_not_allowed() -> None:
    with pytest.raises(MKUserError, match="Password must not be empty"):
        _auth_options_to_internal_format(
            {"auth_type": "password", "enforce_password_change": True, "password": ""},
            PasswordPolicy(12, None),
        )


def test_null_bytes_in_password_not_allowed() -> None:
    with pytest.raises(MKUserError, match="Password must not contain null bytes"):
        _auth_options_to_internal_format(
            {"auth_type": "password", "enforce_password_change": True, "password": "\0"},
            PasswordPolicy(12, None),
        )

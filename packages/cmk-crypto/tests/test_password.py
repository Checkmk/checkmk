#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the Password type"""

import pytest
from cryptography.hazmat.primitives import hashes

from cmk.crypto.hash import HashAlgorithm
from cmk.crypto.password import Password, PasswordPolicy


@pytest.mark.parametrize(
    "password",
    [
        "test 😹",
        "long" * 100,
        "    ",
    ],
)
def test_valid_password(password: str) -> None:
    Password(password)


@pytest.mark.parametrize(
    "password,error",
    [
        ("foo\0bar", "null byte"),
        ("", "empty"),
    ],
)
def test_invalid_password(password: str, error: str) -> None:
    with pytest.raises(ValueError, match=error):
        Password(password)


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (Password("😹"), Password("😹"), True),
        (Password("     "), Password(" "), False),
        (Password("123"), 123, False),
    ],
)
def test_password_eq(a: Password, b: Password | int, expected: bool) -> None:
    assert (a == b) == expected


def test_hash_algorithms_from_cryptography() -> None:
    algo = HashAlgorithm.from_cryptography(hashes.SHA512())
    assert algo == HashAlgorithm.Sha512
    assert algo.name.lower() == hashes.SHA512().name.lower()


def test_hash_algorithms_from_cryptography_unsupported() -> None:
    with pytest.raises(ValueError):
        HashAlgorithm.from_cryptography(hashes.MD5())  # nosec


OK = PasswordPolicy.Result.OK
TooShort = PasswordPolicy.Result.TooShort
TooSimple = PasswordPolicy.Result.TooSimple


@pytest.mark.parametrize(
    "password,min_len,min_grp,expected",
    [
        ("a", 0, 0, OK),
        ("a", None, None, OK),
        ("cmk", 3, 1, OK),
        ("cmk", 4, 1, TooShort),
        ("abc123", None, 3, TooSimple),
        ("abc123", 10, 3, TooShort),  # too short takes precedence
        ("aB1!", 4, 4, OK),
    ],
)
def test_password_policy(
    password: str, min_len: int, min_grp: int, expected: PasswordPolicy.Result
) -> None:
    assert Password(password).verify_policy(PasswordPolicy(min_len, min_grp)) == expected

#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.crypto import password_hashing as ph
from cmk.utils.crypto.password import Password, PasswordHash


@pytest.mark.parametrize("password", ["blä", "😀", "😀" * 18, "a" * 72])
def test_hash_verify_roundtrip(password: str) -> None:
    pw_hash = ph.hash_password(Password(password))
    assert pw_hash.startswith("$2y$04$")  # bcrypt 4 rounds
    ph.verify(Password(password), pw_hash)


def test_hash_no_white_space_trimming() -> None:
    with pytest.raises(ph.PasswordInvalidError):
        ph.verify(Password(" "), ph.hash_password(Password("    ")))


def test_bcrypt_null_bytes() -> None:
    with pytest.raises(ValueError):
        ph.hash_password(Password("foo\0bar"))


@pytest.mark.parametrize("password", [" " * 73, "🙀" * 19])
def test_bcrypt_too_long(password: str) -> None:
    with pytest.raises(ph.PasswordTooLongError):
        ph.hash_password(Password(password))


@pytest.mark.parametrize(
    "valid_hash",
    [
        "$2b$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa",
        # the deprecated 2y bcrypt label is used by `htpasswd -B`
        "$2y$04$gJMIcys.lfgVjCJHje1nkOs4e7klgmoxWWEbaJK6p.jtww7BxDX1K",
    ],
)
def test_verify(valid_hash: str) -> None:
    ph.verify(Password("foobar"), PasswordHash(valid_hash))


@pytest.mark.parametrize(
    "password,password_hash",
    [
        ("raboof", "$2b$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa"),
        # password too long for bcrypt, but fail with regular "wrong password" error
        (75 * "a", "$2b$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa"),
    ],
)
def test_verify_invalid_password_failure(password: str, password_hash: str) -> None:
    with pytest.raises(ph.PasswordInvalidError):
        ph.verify(Password(password), PasswordHash(password_hash))


@pytest.mark.parametrize(
    "password,password_hash",
    [
        ("garbage_hash", "0123abcd"),
        ("empty_hash", ""),
        ("bad_algo", "$pbkdf2-sha256$5$n7O2NmaMMeZ87w$1q0e9XwOYpkcY2E1rYGpP1MChmGdKdQDFzuZIzGOML0"),
        # no longer supported hashes
        (
            "foo",
            "$5$rounds=1000$.J4mcfJGFGgWJA7R$bDhUCLMe2v1.L3oWclfsVYMyOhsS/6RmyzqFRyCgDi/",
        ),  # sha256_crypt
        (
            "foo",
            "$5$H2kwlVdGl9PLMISm$RrQUaIqzFzHmW7SjvCRGV4LsHM2WBT4B0OaGm7TIFI9",
        ),  # sha256_crypt without rounds (defaults to 5000)
        ("foo", "$1$49rn5.0y$XoUJMucpN.aQUEOquaj5C/"),  # md5_crypt
        ("foo", "$apr1$EpPwa/X9$TB2UcQxmrSTJWQQcwHzJM/"),  # apr_md5_crypt
        ("foo", "WsbFVbJdvDcpY"),  # des_crypt
    ],
)
def test_verify_invalid_hash_failure(password: str, password_hash: str) -> None:
    with pytest.raises(ValueError, match="Invalid hash"):
        ph.verify(Password(password), PasswordHash(password_hash))


@pytest.mark.parametrize(
    "password,password_hash",
    [
        # NUL in password
        ("foo\0bar", "$2b$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa"),
        ("foo\0bar", "$5$rounds=1000$.J4mcfJGFGgWJA7R$bDhUCLMe2v1.L3oWclfsVYMyOhsS/6RmyzqFRyCgDi/"),
        # NUL in hash
        ("foobar", "$2b$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2ly\0a"),
        ("foobar", "$2y$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2ly\0a"),
        ("foobar", "$5$rounds=1000$.J4mcfJGFGgWJA7R$bDhUCLMe2v1.L3oWclfsVYMyOhsS/6RmyzqFRyCg\0i/"),
    ],
)
def test_verify_null_bytes(password: str, password_hash: str) -> None:
    with pytest.raises(ValueError):
        ph.verify(Password(password), PasswordHash(password_hash))


@pytest.mark.parametrize(
    "password,pw_hash",
    [
        ("foobar", "$2b$03$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa"),
        ("foobar", "$2b$32$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa"),
        ("foobar", "$2y$32$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa"),
    ],
)
def test_verify_invalid_rounds(password: str, pw_hash: str) -> None:
    with pytest.raises(ValueError, match="rounds"):
        ph.verify(Password(password), PasswordHash(pw_hash))


@pytest.mark.parametrize(
    "unsupported,pw_hash",
    [
        (True, "$1$49rn5.0y$XoUJMucpN.aQUEOquaj5C/"),
        (True, "$apr1$EpPwa/X9$TB2UcQxmrSTJWQQcwHzJM/"),
        (True, "WsbFVbJdvDcpY"),
        (True, "$5$rounds=1000$.J4mcfJGFGgWJA7R$bDhUCLMe2v1.L3oWclfsVYMyOhsS/6RmyzqFRyCgDi/"),
        (False, "foobar"),  # ignore unrecognized algorithms
        (False, ""),
        (False, "$2b$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa"),
        (False, "$2y$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa"),
    ],
)
def test_is_unsupported_legacy_hash(unsupported: bool, pw_hash: str) -> None:
    assert ph.is_unsupported_legacy_hash(PasswordHash(pw_hash)) == unsupported

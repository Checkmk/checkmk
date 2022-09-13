#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable

import pytest
from _pytest.monkeypatch import MonkeyPatch

from cmk.utils.crypto import password_hashing as ph


@pytest.fixture(autouse=True)
def reduce_rounds(monkeypatch: MonkeyPatch) -> None:
    """Reduce the number of rounds for hashing bcrypt and sha256_crypt to their respective minima"""
    monkeypatch.setattr("cmk.utils.crypto.password_hashing.BCRYPT_ROUNDS", 4)
    monkeypatch.setattr("cmk.utils.crypto.password_hashing.SHA256_CRYPT_ROUNDS", 1000)


@pytest.mark.parametrize(
    "algo,identifier,len_checksum",
    [
        (ph.hash_password, "$2b$04$", 43),  # bcrypt
        (ph.sha256_crypt, "$5$rounds=1000$", 31),
    ],
)
@pytest.mark.parametrize("password", ["", "blä", "😀", "😀" * 18, "a" * 72])
def test_hash_verify_roundtrip(
    algo: Callable,
    identifier: str,
    len_checksum: int,
    password: str,
) -> None:
    pw_hash = algo(password)

    assert pw_hash.startswith(identifier)
    assert len(pw_hash) > len(identifier) + len_checksum  # length of included salt may vary

    ph.verify(password, pw_hash)


def test_hash_no_white_space_trimming() -> None:
    with pytest.raises(ph.PasswordInvalidError):
        ph.verify(" ", ph.hash_password("    "))


@pytest.mark.parametrize("algo", [ph.sha256_crypt, ph.hash_password])
def test_bcrypt_null_bytes(algo: Callable) -> None:
    # Note: pyca/bcrypt 4.0 removes this limitation, so this test is bound to fail.
    with pytest.raises(ValueError, match=r".*(NULL|null) (byte|character).*"):
        algo("foo\0bar")


@pytest.mark.parametrize("password", [" " * 73, "🙀" * 19])
def test_bcrypt_too_long(password: str) -> None:
    with pytest.raises(ph.PasswordTooLongError):
        ph.hash_password(password)


@pytest.mark.parametrize(
    "valid_hash",
    [
        "$5$rounds=1000$.J4mcfJGFGgWJA7R$bDhUCLMe2v1.L3oWclfsVYMyOhsS/6RmyzqFRyCgDi/",  # sha256_crypt
        "$2b$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa",  # bcrypt
        # the deprecated 2y label is used by `htpasswd -B`
        "$2y$04$gJMIcys.lfgVjCJHje1nkOs4e7klgmoxWWEbaJK6p.jtww7BxDX1K",  # bcrypt
        # legacy hashes we currently allow
        "$1$49rn5.0y$XoUJMucpN.aQUEOquaj5C/",  # md5_crypt
        "$apr1$EpPwa/X9$TB2UcQxmrSTJWQQcwHzJM/",  # apr_md5_crypt
        "WsbFVbJdvDcpY",  # des_crypt
    ],
)
def test_verify(valid_hash: str) -> None:
    ph.verify("foobar", valid_hash)


@pytest.mark.parametrize(
    "password,password_hash",
    [
        ("raboof", "$2b$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa"),
        ("", "$2b$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa"),
        # password too long for bcrypt, but fail with regular "wrong password" error
        (75 * "a", "$2b$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa"),
    ],
)
def test_verify_invalid_password_failure(password: str, password_hash: str) -> None:
    with pytest.raises(ph.PasswordInvalidError):
        ph.verify(password, password_hash)


@pytest.mark.parametrize(
    "password,password_hash",
    [
        ("garbage_hash", "0123abcd"),
        ("empty_hash", ""),
        ("bad_algo", "$pbkdf2-sha256$5$n7O2NmaMMeZ87w$1q0e9XwOYpkcY2E1rYGpP1MChmGdKdQDFzuZIzGOML0"),
    ],
)
def test_verify_invalid_hash_failure(password: str, password_hash: str) -> None:
    # Note: In version 1.7.2 passlib may directly raise a ValueError, rather than an UnknownHashError
    #       that we convert to a ValueError in password_hashing.verify. So we don't match for the
    #       error message here.
    with pytest.raises(ValueError):
        ph.verify(password, password_hash)


@pytest.mark.parametrize(
    "password,password_hash",
    [
        # NUL in password
        ("foo\0bar", "$2b$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa"),
        ("foo\0bar", "$5$rounds=1000$.J4mcfJGFGgWJA7R$bDhUCLMe2v1.L3oWclfsVYMyOhsS/6RmyzqFRyCgDi/"),
        # NUL in hash
        ("foobar", "$2b$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2ly\0a"),
        ("foobar", "$5$rounds=1000$.J4mcfJGFGgWJA7R$bDhUCLMe2v1.L3oWclfsVYMyOhsS/6RmyzqFRyCg\0i/"),
    ],
)
def test_verify_null_bytes(password: str, password_hash: str) -> None:
    with pytest.raises(ValueError):
        ph.verify(password, password_hash)


@pytest.mark.parametrize(
    "pw_hash",
    [
        "$5$rounds=5000$H2kwlVdGl9PLMISm$RrQUaIqzFzHmW7SjvCRGV4LsHM2WBT4B0OaGm7TIFI9",
        "$5$H2kwlVdGl9PLMISm$RrQUaIqzFzHmW7SjvCRGV4LsHM2WBT4B0OaGm7TIFI9",
    ],
)
def test_verify_sha256_omit_rounds(pw_hash: str) -> None:
    """
    The rounds parameter in the hash specification for sha256-crypt may be or may not be omitted to
    indicate 5000 rounds.
    https://passlib.readthedocs.io/en/stable/lib/passlib.hash.sha256_crypt.html#passlib.hash.sha256_crypt
    """
    ph.verify("foobar", pw_hash)


@pytest.mark.parametrize(
    "password,pw_hash",
    [
        ("foobar", "$2b$03$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa"),
        ("foobar", "$2b$32$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa"),
        ("foobar", "$5$rounds=999$H2kwlVdGl9PLMISm$RrQUaIqzFzHmW7SjvCRGV4LsHM2WBT4B0OaGm7TIFI9"),
        (
            "foobar",
            "$5$rounds=1000000000$H2kwlVdGl9PLMISm$RrQUaIqzFzHmW7SjvCRGV4LsHM2WBT4B0OaGm7TIFI9",
        ),
    ],
)
def test_verify_invalid_rounds(password: str, pw_hash: str) -> None:
    with pytest.raises(ValueError, match="rounds"):
        ph.verify(password, pw_hash)

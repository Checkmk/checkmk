#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module implements password hashing and validation of password hashes.

At the moment it wraps the respective functionality from passlib, with the goal of replacing
passlib in the future.
"""

from typing import Optional

# TODO: Import errors from passlib are suppressed right now since now
# stub files for mypy are not available.
from passlib import hash as passlib_hash  # type: ignore[import]
from passlib.context import CryptContext  # type: ignore[import]
from passlib.exc import PasswordTruncateError  # type: ignore[import]

from cmk.utils.exceptions import MKException


class PasswordTooLongError(MKException):
    """Indicates that the provided password is too long to be used

    Currently this will happen when trying to hash a password longer than
    72 bytes with bcrypt. See hash_password for more details.
    """


def hash_password(password: str, *, rounds: Optional[int] = None) -> str:
    """Hash a password using bcrypt

    :param password: The password to hash.
    :param rounds: Number of bcrypt rounds to use. This parameter is only used to reduce the
                   runtime of unit tests. Production code should always use the default (12).
                   Must be at least 4.

    :return: The hashed password concatenated with the necessary information to validate the hash
             in the so-called Modular Crypto Format. The result string has the form
               $2b${rounds}${salt}{checksum}
             See also:
               https://passlib.readthedocs.io/en/stable/modular_crypt_format.html#modular-crypt-format.

    :raise: PasswordTooLongError if the provided password is longer than 72 bytes.
    :raise: ValueError if fewer than 4 rounds are selected or if the input password contains
            null bytes.

    The output of hash_password functions as the input for check_password:
        >>> check_password("foobar", hash_password("foobar", rounds=4))
        True

    Empty passwords are also hashed:
        >>> "$2b$04$" in hash_password("", rounds=4)
        True

    hash_password will fail as follows:
        >>> hash_password("", rounds=3)
        Traceback (most recent call last):
            ...
        ValueError: ...

        >>> "$2b$04$" in hash_password("bar\0foo", rounds=4)
        Traceback (most recent call last):
            ...
        ValueError: source code string cannot contain null bytes

        >>> hash_password(73*"a", rounds=4)
        Traceback (most recent call last):
            ...
        cmk.utils.crypto.password_hashing.PasswordTooLongError: Password too long (bcrypt truncates to 72 characters)
    """
    # NOTE: The time for hashing is *exponential* in the number of rounds, so this
    # can get *very* slow! On a laptop with a i9-9880H CPU, the runtime is roughly
    # 43 microseconds * 2**rounds, so for 12 rounds this takes about 0.176s.
    # Nevertheless, the rounds a.k.a. workfactor should be more than 10 for security
    # reasons. It defaults to 12, but let's be explicit.
    try:
        return passlib_hash.bcrypt.using(
            rounds=12 if rounds is None else rounds,
            truncate_error=True,
        ).hash(password)
    except PasswordTruncateError as e:
        raise PasswordTooLongError(e)


def sha256_crypt(password: str) -> str:
    return passlib_hash.sha256_crypt.hash(password)


_default_policy = CryptContext(
    schemes=[
        "bcrypt",
        # Kept for compatibility with Checkmk < 2.1
        "sha256_crypt",
        # Kept for compatibility with Checkmk < 1.6
        # htpasswd has still md5 as default, also the docs include the "-m" param
        "md5_crypt",
        "apr_md5_crypt",
        "des_crypt",
    ]
)


def check_password(password: str, pwhash: str) -> bool:
    """Validate a password given a password hash

    :param password: The plaintext password.
    :param pwhash: The hash of the password along with meta information about the hash algorithm
                   that was used, as output by hash_password.

    :return: True iff the password is valid.

    The algorithm to use, the number of rounds, and, where applicable, the salt are detected from
    the input string:
    sha256-crypto:
        >>> check_password("foobar", "$5$rounds=1000$.J4mcfJGFGgWJA7R$bDhUCLMe2v1.L3oWclfsVYMyOhsS/6RmyzqFRyCgDi/")
        True

    bcrypt:
        >>> check_password("foobar", "$2b$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa")
        True
        >>> check_password("raboof", "$2b$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa")
        False
        >>> check_password("", "$2b$04$5LiM0CX3wUoO55cGCwrkDeZIU5zyBqPDZfV9zU4Q2WH/Lkkn2lypa")
        False
        >>> check_password("empty_hash", "")
        False

    The rounds parameter in the hash specification for sha256-crypt may be omitted to indicate 5000 rounds.
    (https://passlib.readthedocs.io/en/stable/lib/passlib.hash.sha256_crypt.html#passlib.hash.sha256_crypt)
        >>> check_password("foobar", "$5$H2kwlVdGl9PLMISm$RrQUaIqzFzHmW7SjvCRGV4LsHM2WBT4B0OaGm7TIFI9")
        True

    ... or not omitted.
        >>> check_password("foobar", "$5$rounds=5000$H2kwlVdGl9PLMISm$RrQUaIqzFzHmW7SjvCRGV4LsHM2WBT4B0OaGm7TIFI9")
        True

    The hash algorithm must be allowed in _crypt_context. Otherwise validation fails.
        >>> check_password("password", "$pbkdf2-sha256$5$n7O2NmaMMeZ87w$1q0e9XwOYpkcY2E1rYGpP1MChmGdKdQDFzuZIzGOML0")
        False
    """
    # NOTE: The same warning regarding runtime is applicable here, the runtime for
    # verification is roughly the same as for the hashing above.
    try:
        return _default_policy.verify(password, pwhash)
    except ValueError:
        # TODO: make this throw so using code MUST deal with the error.
        # ValueError("hash could not be identified")
        # Is raised in case of locked users because we prefix the hashes with
        # a "!" sign in this situation.
        return False

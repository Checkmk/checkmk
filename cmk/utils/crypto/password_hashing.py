#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module implements password hashing and validation of password hashes.

At the moment it wraps the respective functionality from passlib, with the goal of replacing
passlib in the future.

The password hashing functions return hashes in the Modular Crypto Format
(https://passlib.readthedocs.io/en/stable/modular_crypt_format.html#modular-crypt-format).
The format contains an identifier for the hash algorithm that was used, the number of rounds,
a salt, and the actual checksum -- which is all the information needed to verify the hash with a
given password (see `verify`).
"""

from collections.abc import Sequence

# TODO: Import errors from passlib are suppressed right now since now
# stub files for mypy are not available.
import passlib.context  # type: ignore[import]
import passlib.exc  # type: ignore[import]
from passlib import hash as passlib_hash

from cmk.utils.exceptions import MKException

# Using code should not be able to change the number of rounds (to unsafe values), but test code
# has to run with reduced rounds. They can be monkeypatched here.
BCRYPT_ROUNDS = 12


class PasswordTooLongError(MKException):
    """Indicates that the provided password is too long to be used

    Currently this will happen when trying to hash a password longer than 72 bytes due to
    restrictions of bcrypt.
    """


class PasswordInvalidError(MKException):
    """Indicates that the provided password could not be verified"""


def hash_password(password: str) -> str:
    """Hash a password using the preferred algorithm

    Uses bcrypt with 12 rounds to hash a password.

    :param password: The password to hash. The password must not be longer than 72 bytes.

    :return: The hashed password Modular Crypto Format (see module docstring). The identifier for
             bcrypt is "2b".

    :raise: PasswordTooLongError if the provided password is longer than 72 bytes.
    :raise: ValueError if the input password contains null bytes.
    """
    try:
        return passlib_hash.bcrypt.using(
            rounds=BCRYPT_ROUNDS, truncate_error=True, ident="2y"
        ).hash(password)
    except passlib.exc.PasswordTruncateError as e:
        raise PasswordTooLongError(e)


def _allowed_schemes() -> Sequence[str]:
    """List of hash algorithms allowed in `verify`

    While using code should no longer select an algorithm itself (but use `hash_password` instead),
    we still have to account for existing passwords created with now-deprecated schemes and created
    by external tools (notably `htpasswd -m`).
    """
    return [
        "bcrypt",  # Preferred and default for hashing
        "sha256_crypt",  # Kept for compatibility with Checkmk < 2.1
        # Kept for compatibility with Checkmk < 1.6
        # htpasswd has still md5 as default, also the docs include the "-m" param
        "md5_crypt",
        "apr_md5_crypt",
        "des_crypt",
    ]


def verify(password: str, password_hash: str) -> None:
    """Verify if a password matches a password hash.

    :param password: The password to check.
    :param password_hash: The password hash to check.

    :return: None

    :raise: PasswordInvalidError if the password does not match the hash.
    :raise: ValueError - if the hash algorithm in `password_hash` could not be identified.
                       - if the identified hash algorithm specifies too few rounds.
                       - if `password` or `password_hash` contain invalid characters (e.g. NUL).
    """
    try:
        valid = passlib.context.CryptContext(schemes=_allowed_schemes()).verify(
            password, password_hash
        )
    except passlib.exc.UnknownHashError:
        raise ValueError("Invalid hash")
    if not valid:
        raise PasswordInvalidError

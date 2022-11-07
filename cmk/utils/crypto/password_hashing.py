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

from typing import AnyStr

# TODO: Import errors from passlib are suppressed right now since now
# stub files for mypy are not available.
import passlib.context  # type: ignore[import]
import passlib.exc  # type: ignore[import]
from passlib import hash as passlib_hash

from cmk.utils.crypto import Password
from cmk.utils.exceptions import MKException

# Using code should not be able to change the number of rounds (to unsafe values), but test code
# has to run with reduced rounds. They can be monkeypatched here.
BCRYPT_ROUNDS = 12
# The default modern bcrypt identifier is "2b", but htpasswd will only accept "2y".
BCRYPT_IDENT = "2y"


class PasswordTooLongError(MKException):
    """Indicates that the provided password is too long to be used

    Currently this will happen when trying to hash a password longer than 72 bytes due to
    restrictions of bcrypt.
    """


class PasswordInvalidError(MKException):
    """Indicates that the provided password could not be verified"""


def hash_password(password: Password[AnyStr], *, allow_truncation=False) -> str:
    """Hash a password using the preferred algorithm

    Uses bcrypt with 12 rounds to hash a password.

    :param password: The password to hash. The password must not be longer than 72 bytes (except if
                     allow_truncation is set).
    :param allow_truncation: Allow passwords longer than 72 bytes and silently truncate them.
                             This should be avoided but is required for some use cases.

    :return: The hashed password Modular Crypto Format (see module docstring). The identifier used
             for bcrypt is "2y" for compatibility with htpasswd.

    :raise: PasswordTooLongError if the provided password is longer than 72 bytes.
    :raise: ValueError if the input password contains null bytes.
    """
    try:
        return passlib_hash.bcrypt.using(
            rounds=BCRYPT_ROUNDS, truncate_error=not allow_truncation, ident=BCRYPT_IDENT
        ).hash(password.raw)
    except passlib.exc.PasswordTruncateError as e:
        raise PasswordTooLongError(e)


# Created by Checkmk < 2.1:
_deprecated_algos = ["sha256_crypt"]
# Created by Checkmk < 1.6:
_insecure_algos = ["md5_crypt", "apr_md5_crypt", "des_crypt"]

_context = passlib.context.CryptContext(
    # All new hashes we create (using hash_password() will use bcrypt. However, we still have to
    # account for existing passwords created with now-deprecated schemes.
    schemes=["bcrypt"] + _deprecated_algos + _insecure_algos,
    # Hashes marked "deprecated" will automatically be updated to bcrypt. We only update
    # sha256-crypt. Older hashes are not auto-updated -- users should make a new password.
    deprecated=_deprecated_algos,
    bcrypt__ident=BCRYPT_IDENT,
)


def verify(password: Password[AnyStr], password_hash: str) -> None:
    """Verify if a password matches a password hash.

    :param password: The password to check.
    :param password_hash: The password hash to check.

    :return: None if the password is valid; raises an exception otherwise (see below).

    :raise: PasswordInvalidError if the password does not match the hash.
    :raise: ValueError - if the hash algorithm in `password_hash` could not be identified.
                       - if the identified hash algorithm specifies too few rounds.
                       - if `password` or `password_hash` contain invalid characters (e.g. NUL).
    """
    try:
        valid = _context.verify(password.raw, password_hash)
    except passlib.exc.UnknownHashError:
        raise ValueError("Invalid hash")
    if not valid:
        raise PasswordInvalidError


def needs_update(password_hash: str) -> bool:
    """Check if a password hash should be re-calculated because the hash algorithm is deprecated.

    See _context for the list of deprecated algorithms.
    """
    return _context.needs_update(password_hash)


def is_insecure_hash(password_hash: str) -> bool:
    """Is the hash algorithm used for this hash considered insecure"""
    return _context.identify(password_hash, required=False) in _insecure_algos

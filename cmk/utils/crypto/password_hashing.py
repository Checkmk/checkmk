#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
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
import logging
import sys

# Import errors from passlib are suppressed since stub files for mypy are not available.
# pylint errors are suppressed since this is the only module that should import passlib.
import passlib.context  # type: ignore[import]  # pylint: disable=passlib-module-import
import passlib.exc  # type: ignore[import]  # pylint: disable=passlib-module-import
from passlib import hash as passlib_hash  # pylint: disable=passlib-module-import

from cmk.utils.crypto.password import Password, PasswordHash
from cmk.utils.exceptions import MKException

logger = logging.getLogger(__name__)

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


def hash_password(password: Password, *, allow_truncation: bool = False) -> PasswordHash:
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
        return PasswordHash(
            passlib_hash.bcrypt.using(
                rounds=BCRYPT_ROUNDS, truncate_error=not allow_truncation, ident=BCRYPT_IDENT
            ).hash(password.raw)
        )
    except passlib.exc.PasswordTruncateError as e:
        raise PasswordTooLongError(e)


_context = passlib.context.CryptContext(
    # The only scheme we support is bcrypt. This includes the regular '$2b$' form of the hash,
    # as well as Apache's legacy form '$2y$' (which we currently also create).
    #
    # Other hashing schemes that were supported in the past should have been migrated to bcrypt
    # with Werk #14391. For the record, hashes that could be encountered on old installations were
    # sha256_crypt, md5_crypt, apr_md5_crypt and des_crypt.
    schemes=["bcrypt"],
    # There are currently no "deprecated" algorithms that we auto-update on login.
    deprecated=[],
    bcrypt__ident=BCRYPT_IDENT,
)


def verify(password: Password, password_hash: PasswordHash) -> None:
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
        logger.warning(
            "Invalid hash. Only bcrypt is supported.",
            exc_info=sys.exc_info(),
        )
        raise ValueError("Invalid hash")
    if not valid:
        raise PasswordInvalidError


def needs_update(password_hash: PasswordHash) -> bool:
    """Check if a password hash should be re-calculated because the hash algorithm is deprecated.

    See _context for the list of deprecated algorithms.
    """
    return _context.needs_update(password_hash)


def is_unsupported_legacy_hash(password_hash: PasswordHash) -> bool:
    """Was the hash algorithm used for this hash once supported but isn't anymore?"""
    legacy = ["sha256_crypt", "md5_crypt", "apr_md5_crypt", "des_crypt"]
    return (
        passlib.context.CryptContext(schemes=legacy + ["bcrypt"]).identify(
            password_hash, required=False
        )
        in legacy
    )

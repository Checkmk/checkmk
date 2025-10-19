#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import hashlib
import os
from collections.abc import Mapping
from pathlib import Path
from typing import final

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class PasswordStoreError(RuntimeError):
    pass


class Secret[T]:
    """A class to hold secrets.

    This class is a simple protection against accidental logging of secrets:

    >>> s = Secret("s3cr37!")
    >>> # it will not show in strings or reprs:
    >>> print(s)
    '****'
    >>> repr(s)
    'Secret(****)'
    >>> # but you can still get the value:
    >>> s.reveal()
    's3cr37!'

    """

    def __init__(self, value: T, /) -> None:
        self._value = value

    def __repr__(self) -> str:
        """Return a string omitting the actual value.

        This deliberately breaks the semantics of __repr__ in favour of not leaking secrets:
        """
        return f"Secret('{self}')"

    def __str__(self) -> str:
        return "****"

    def reveal(self) -> T:
        return self._value


@final
class PasswordStore:
    """A password store that can load and save passwords in an encrypted file.

    **This is not intended to be used by plugins directly!**
    """

    _VERSION = 0
    _VERSION_BYTE_LENGTH = 2

    _SALT_LENGTH: int = 16
    _NONCE_LENGTH: int = 16
    _AEAD_TAG_LENGTH: int = 16

    # CMK-16660
    # _PASSWORD_ID_PREFIX = ":uuid:"  # cannot collide with user defined id.
    _PASSWORD_ID_PREFIX = "uuid"

    def __init__(self, secret: Secret[bytes], /) -> None:
        self._secret = secret

    def load_bytes(self, raw: bytes) -> Mapping[str, Secret[str]]:
        return self._deserialise(self._decrypt(raw))

    def dump_bytes(self, passwords: Mapping[str, Secret[str]]) -> bytes:
        return self._encrypt(self._serialize(passwords))

    @staticmethod
    def _serialize(passwords: Mapping[str, Secret[str]]) -> str:
        return "".join(
            f"{ident}:{password.reveal()}\n" for ident, password in passwords.items()
        )

    @classmethod
    def _deserialise(cls, raw: str) -> Mapping[str, Secret[str]]:
        """
        This is designed to work with a _PASSWORD_ID_PREFIX that
        contains a colon at the beginning and the end, but
        that is not supported by the other implementations.
        """
        # watch out. Crashing here might leak sensitive data.
        passwords = dict[str, Secret[str]]()
        try:
            for line in raw.splitlines():
                if (sline := line.strip()).startswith(cls._PASSWORD_ID_PREFIX):
                    uuid = sline.removeprefix(cls._PASSWORD_ID_PREFIX).split(":", 1)[0]
                    password = Secret(
                        sline.removeprefix(cls._PASSWORD_ID_PREFIX).split(":", 1)[1]
                    )
                    ident = f"{cls._PASSWORD_ID_PREFIX}{uuid}"
                else:
                    ident = sline.split(":", 1)[0]
                    password = Secret(sline.split(":", 1)[1])

                passwords[ident] = password
        finally:
            pass  # raw = line = sline = "<redacted>"  # wipe sensitive data

        return passwords

    def _encrypt(self, plaintext: str, /) -> bytes:
        salt = os.urandom(self._SALT_LENGTH)
        nonce = os.urandom(self._NONCE_LENGTH)
        encrypted = AESGCM(self._derive_secret_key(salt)).encrypt(
            nonce, plaintext.encode("utf-8"), associated_data=None
        )
        return (
            self._VERSION.to_bytes(self._VERSION_BYTE_LENGTH, byteorder="big")
            + salt
            + nonce
            + encrypted[-self._AEAD_TAG_LENGTH :]
            + encrypted[: -self._AEAD_TAG_LENGTH]
        )

    def _decrypt(self, raw: bytes, /) -> str:
        _version, rest = (
            raw[: self._VERSION_BYTE_LENGTH],
            raw[self._VERSION_BYTE_LENGTH :],
        )
        salt, rest = rest[: self._SALT_LENGTH], rest[self._SALT_LENGTH :]
        nonce, rest = rest[: self._NONCE_LENGTH], rest[self._NONCE_LENGTH :]
        tag, encrypted = rest[: self._AEAD_TAG_LENGTH], rest[self._AEAD_TAG_LENGTH :]
        return (
            AESGCM(self._derive_secret_key(salt))
            .decrypt(nonce, encrypted + tag, associated_data=None)
            .decode("utf-8")
        )

    def _derive_secret_key(self, salt: bytes) -> bytes:
        """Derive a symmetric key from the local secret"""
        # TODO: in a future step (that requires migration of passwords) we could switch to HKDF.
        # Scrypt is slow by design but that isn't necessary here because the secret is not just a
        # password but "real" random data.
        # Note that key derivation and encryption/decryption of passwords is duplicated in omd
        # cmk_password_store.h and must be kept compatible!
        return hashlib.scrypt(
            self._secret.reveal(), salt=salt, n=2**14, r=8, p=1, dklen=32
        )


def _load(
    store_file: Path,
    key_file: Path,
) -> Mapping[str, Secret[str]]:
    try:
        store_bytes = store_file.read_bytes()
    except FileNotFoundError:
        # We might well have never written any passwords. This is not an error.
        return {}

    try:
        store_secret = Secret(key_file.read_bytes())
    except FileNotFoundError as exc:
        raise PasswordStoreError(
            f"Password store key file not found. Cannot decrypt {store_file}"
        ) from exc

    return PasswordStore(store_secret).load_bytes(store_bytes)


def dereference_secret(raw: str, /) -> Secret[str]:
    """Look up the password with id <id> in the file <file> and return it.

    Raises:
        ValueError

    Returns:
        The password as found in the password store.
    """
    if not (raw_key_file := os.environ.get("PASSWORD_STORE_SECRET_FILE")):
        raise PasswordStoreError(
            "Environment variable PASSWORD_STORE_SECRET_FILE is not set"
        )

    secret_id, pws_path = raw.split(":", 1)
    store = _load(store_file=Path(pws_path), key_file=Path(raw_key_file))
    try:
        return store[secret_id]
    except KeyError:
        # the fact that this is a dict is an implementation detail.
        raise PasswordStoreError(f"Password '{secret_id}' not found in {pws_path}")

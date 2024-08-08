#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

from flask import session

from cmk.crypto.secrets import Secret
from cmk.crypto.symmetric import aes_gcm_decrypt, aes_gcm_encrypt, TaggedCiphertext


class Encrypter:
    """Helper to encrypt site secrets

    The secrets are encrypted using the auth.secret which is only known to the local and remotely
    configured sites.
    """

    # TODO: This shares almost all the code with PasswordStore, except for the version bytes that
    # are prepended by the store.

    SALT_LENGTH: int = 16
    NONCE_LENGTH: int = 16

    @staticmethod
    def _get_secret() -> Secret:
        assert hasattr(session, "session_info")  # mypy
        return Secret.from_b64(session.session_info.encrypter_secret)

    @staticmethod
    def encrypt(value: str) -> bytes:
        salt = os.urandom(Encrypter.SALT_LENGTH)
        nonce = os.urandom(Encrypter.NONCE_LENGTH)
        key = Encrypter._get_secret().hmac(salt)
        encrypted = aes_gcm_encrypt(key, nonce, value)
        return salt + nonce + encrypted.tag + encrypted.ciphertext

    @staticmethod
    def decrypt(raw: bytes) -> str:
        salt, rest = raw[: Encrypter.SALT_LENGTH], raw[Encrypter.SALT_LENGTH :]
        nonce, rest = rest[: Encrypter.NONCE_LENGTH], rest[Encrypter.NONCE_LENGTH :]
        tag, encrypted = rest[: TaggedCiphertext.TAG_LENGTH], rest[TaggedCiphertext.TAG_LENGTH :]
        key = Encrypter._get_secret().hmac(salt)
        return aes_gcm_decrypt(key, nonce, TaggedCiphertext(ciphertext=encrypted, tag=tag))

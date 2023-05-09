#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides commonly used functions for the handling of encrypted
data within the Checkmk ecosystem."""

from typing import Callable, Tuple, TYPE_CHECKING

from Cryptodome.Cipher import AES
from Cryptodome.Hash import SHA256
from Cryptodome.Protocol.KDF import PBKDF2
from OpenSSL import crypto  # type: ignore[import]

if TYPE_CHECKING:
    import hashlib

OPENSSL_SALTED_MARKER = "Salted__"


def decrypt_aes_256_cbc_pbkdf2(
    ciphertext: bytes,
    password: str,
) -> bytes:
    """Decrypt an openssl encrypted bytestring:
    Cipher: AES256-CBC
    Salted: yes
    Key Derivation: PKBDF2, with SHA256 digest, 10000 cycles
    """
    SALT_LENGTH = 8
    KEY_LENGTH = 32
    IV_LENGTH = 16
    PBKDF2_CYCLES = 10_000

    salt = ciphertext[:SALT_LENGTH]
    raw_key = PBKDF2(password,
                     salt,
                     KEY_LENGTH + IV_LENGTH,
                     count=PBKDF2_CYCLES,
                     hmac_hash_module=SHA256)
    key, iv = raw_key[:KEY_LENGTH], raw_key[KEY_LENGTH:]

    decryption_suite = AES.new(key, AES.MODE_CBC, iv)
    decrypted_pkg = decryption_suite.decrypt(ciphertext[SALT_LENGTH:])

    return _strip_fill_bytes(decrypted_pkg)


def decrypt_aes_256_cbc_legacy(
    ciphertext: bytes,
    password: str,
    digest: Callable[..., "hashlib._Hash"],
) -> bytes:
    """Decrypt an openssl encrypted bytesting:
    Cipher: AES256-CBC
    Salted: no
    Key derivation: Simple OpenSSL Key derivation
    """
    key, iv = _derive_openssl_key_and_iv(password.encode("utf-8"), digest, 32, AES.block_size)

    decryption_suite = AES.new(key, AES.MODE_CBC, iv)
    decrypted_pkg = decryption_suite.decrypt(ciphertext)

    return _strip_fill_bytes(decrypted_pkg)


def _derive_openssl_key_and_iv(
    password: bytes,
    digest: Callable[..., "hashlib._Hash"],
    key_length: int,
    iv_length: int,
) -> Tuple[bytes, bytes]:
    """Simple OpenSSL Key derivation function
    """
    d = d_i = b""
    while len(d) < key_length + iv_length:
        d_i = digest(d_i + password).digest()
        d += d_i
    return d[:key_length], d[key_length:key_length + iv_length]


def _strip_fill_bytes(content: bytes) -> bytes:
    return content[0:-content[-1]]


def sign_key_fingerprint(certificate: bytes) -> str:
    """Get the fingerprint using the sign key's certificate"""
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, certificate)
    return cert.digest("sha256").decode('utf-8')

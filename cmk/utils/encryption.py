#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides commonly used functions for the handling of encrypted
data within the Checkmk ecosystem."""

import enum
import hashlib
from typing import Callable, List, NamedTuple, Tuple

from Cryptodome.Cipher import AES
from Cryptodome.Hash import SHA256
from Cryptodome.Protocol.KDF import PBKDF2
from cryptography import x509
from cryptography.x509.oid import ExtensionOID
from OpenSSL import crypto, SSL  # type: ignore[import]

OPENSSL_SALTED_MARKER = "Salted__"


class TransportProtocol(enum.Enum):
    PLAIN = b"<<"
    MD5 = b"00"
    SHA256 = b"02"
    PBKDF2 = b"03"
    TLS = b"16"
    NONE = b"99"


def decrypt_by_agent_protocol(
    password: str,
    protocol: TransportProtocol,
    encrypted_pkg: bytes,
) -> bytes:
    """select the decryption algorithm based on the agent header

    Support encrypted agent data with "99" header.
    This was not intended, but the Windows agent accidentally sent this header
    instead of "00" up to 2.0.0p1, so we keep this for a while.

    Warning:
        "99" for real-time check data means "unencrypted"!
    """

    if protocol is TransportProtocol.PBKDF2:
        return _decrypt_aes_256_cbc_pbkdf2(
            ciphertext=encrypted_pkg[len(OPENSSL_SALTED_MARKER) :],
            password=password,
        )

    if protocol is TransportProtocol.SHA256:
        return _decrypt_aes_256_cbc_legacy(
            ciphertext=encrypted_pkg,
            password=password,
            digest=hashlib.sha256,
        )

    return _decrypt_aes_256_cbc_legacy(
        ciphertext=encrypted_pkg,
        password=password,
        digest=hashlib.md5,
    )


def _decrypt_aes_256_cbc_pbkdf2(
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
    raw_key = PBKDF2(
        password, salt, KEY_LENGTH + IV_LENGTH, count=PBKDF2_CYCLES, hmac_hash_module=SHA256
    )
    key, iv = raw_key[:KEY_LENGTH], raw_key[KEY_LENGTH:]

    decryption_suite = AES.new(key, AES.MODE_CBC, iv)
    decrypted_pkg = decryption_suite.decrypt(ciphertext[SALT_LENGTH:])

    return _strip_fill_bytes(decrypted_pkg)


def _decrypt_aes_256_cbc_legacy(
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
    """Simple OpenSSL Key derivation function"""
    d = d_i = b""
    while len(d) < key_length + iv_length:
        d_i = digest(d_i + password).digest()
        d += d_i
    return d[:key_length], d[key_length : key_length + iv_length]


def _strip_fill_bytes(content: bytes) -> bytes:
    return content[0 : -content[-1]]


def is_ca_certificate(crypto_cert: x509.Certificate) -> bool:
    try:
        key_usage = crypto_cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
        use_key_for_signing = key_usage.value.key_cert_sign is True
    except x509.extensions.ExtensionNotFound:
        use_key_for_signing = False

    try:
        basic_constraints = crypto_cert.extensions.get_extension_for_oid(
            ExtensionOID.BASIC_CONSTRAINTS
        )
        is_ca = basic_constraints.value.ca is True
    except x509.extensions.ExtensionNotFound:
        is_ca = False

    return is_ca and use_key_for_signing


class ChainVerifyResult(NamedTuple):
    cert_pem: bytes
    error_number: int
    error_depth: int
    error_message: str
    is_valid: bool


def verify_certificate_chain(
    connection: SSL.Connection, certificate_chain: List[crypto.X509]
) -> List[ChainVerifyResult]:
    verify_chain_results = []

    # Used to record all certificates and verification results for later displaying
    for cert in certificate_chain:
        # This is mainly done to get the textual error message without accessing internals of the SSL modules
        error_number, error_depth, error_message = 0, 0, ""
        try:
            x509_store = connection.get_context().get_cert_store()
            x509_store_context = crypto.X509StoreContext(x509_store, cert)
            x509_store_context.verify_certificate()
        except crypto.X509StoreContextError as e:
            error_number, error_depth, error_message = e.args[0]

        verify_chain_results.append(
            ChainVerifyResult(
                cert_pem=crypto.dump_certificate(crypto.FILETYPE_PEM, cert),
                error_number=error_number,
                error_depth=error_depth,
                error_message=error_message,
                is_valid=error_number == 0,
            )
        )

    return verify_chain_results

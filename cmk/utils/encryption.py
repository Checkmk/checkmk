#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides commonly used functions for the handling of encrypted
data within the Checkmk ecosystem."""

from __future__ import annotations

import binascii
import contextlib
import enum
import errno
import hashlib
import os
import re
import socket
from pathlib import Path
from typing import Callable, Iterable, List, NamedTuple, Tuple

from Cryptodome.Cipher import AES
from Cryptodome.Hash import SHA256
from Cryptodome.Protocol.KDF import PBKDF2
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import ExtensionOID, NameOID
from OpenSSL import crypto, SSL  # type: ignore[import]

import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException

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


_PEM_RE = re.compile(
    "-----BEGIN CERTIFICATE-----\r?.+?\r?-----END CERTIFICATE-----\r?\n?", re.DOTALL
)


def raw_certificates_from_file(path: Path) -> List[str]:
    try:
        # Some users use comments in certificate files e.g. to write the content of the
        # certificate outside of encapsulation boundaries. We only want to extract the
        # certificates between the encapsulation boundaries which have to be 7-bit ASCII
        # characters.
        with path.open("r", encoding="ascii", errors="surrogateescape") as f:
            return [
                content
                for match in _PEM_RE.finditer(f.read())
                if (content := match.group(0)).isascii()
            ]
    except IOError as e:
        if e.errno == errno.ENOENT:
            # Silently ignore e.g. dangling symlinks
            return []
        raise


class CertificateDetails(NamedTuple):
    issued_to: str
    issued_by: str
    valid_from: str
    valid_till: str
    signature_algorithm: str
    digest_sha256: str
    serial_number: int
    is_ca: bool
    verify_result: ChainVerifyResult


class ChainVerifyResult(NamedTuple):
    cert_pem: bytes
    error_number: int
    error_depth: int
    error_message: str
    is_valid: bool


# NOTE: Use this function only in conjunction with the permission server_side_requests
def fetch_certificate_details(
    trusted_ca_file: Path, address_family: socket.AddressFamily, address: Tuple[str, int]
) -> Iterable[CertificateDetails]:
    """Creates a list of certificate details for the chain certs"""
    verify_chain_results = _fetch_certificate_chain_verify_results(
        trusted_ca_file, address_family, address
    )
    if not verify_chain_results:
        raise MKGeneralException("Failed to fetch the certificate chain")

    def get_name(name_obj):
        return name_obj.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value

    for result in verify_chain_results:
        crypto_cert = x509.load_pem_x509_certificate(result.cert_pem, default_backend())
        yield CertificateDetails(
            issued_to=get_name(crypto_cert.subject),
            issued_by=get_name(crypto_cert.issuer),
            valid_from=str(crypto_cert.not_valid_before),
            valid_till=str(crypto_cert.not_valid_after),
            signature_algorithm=crypto_cert.signature_hash_algorithm.name,
            digest_sha256=binascii.hexlify(crypto_cert.fingerprint(hashes.SHA256())).decode(),
            serial_number=crypto_cert.serial_number,
            is_ca=_is_ca_certificate(crypto_cert),
            verify_result=result,
        )


def _is_ca_certificate(crypto_cert: x509.Certificate) -> bool:
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


def _fetch_certificate_chain_verify_results(
    trusted_ca_file: Path,
    address_family: socket.AddressFamily,
    address: Tuple[str, int],
) -> List[ChainVerifyResult]:
    """Opens a SSL connection and performs a handshake to get the certificate chain"""

    ctx = SSL.Context(SSL.SSLv23_METHOD)
    ctx.load_verify_locations(str(trusted_ca_file))

    with contextlib.closing(
        SSL.Connection(ctx, socket.socket(address_family, socket.SOCK_STREAM))
    ) as sock:
        # pylint does not get the object type of sock right
        sock.connect(address)
        sock.do_handshake()
        certificate_store = sock.get_context().get_cert_store()
        certificate_chain = sock.get_peer_cert_chain()

    return _verify_certificate_chain(certificate_store, certificate_chain)


def _verify_certificate_chain(
    x509_store: crypto.X509Store, certificate_chain: List[crypto.X509]
) -> List[ChainVerifyResult]:
    verify_chain_results = []

    # Used to record all certificates and verification results for later displaying
    for cert in certificate_chain:
        # This is mainly done to get the textual error message without accessing internals of the SSL modules
        error_number, error_depth, error_message = 0, 0, ""
        try:
            crypto.X509StoreContext(x509_store, cert).verify_certificate()
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


class Encrypter:
    """Helper to encrypt site secrets

    The secrets are encrypted using the auth.secret which is only known to the local and remotely
    configured sites. The encrypted values are base64 encoded for easier processing.
    """

    @classmethod
    def _secret_key_path(cls) -> Path:
        return cmk.utils.paths.omd_root / "etc" / "auth.secret"

    @classmethod
    def _passphrase(cls) -> bytes:
        with cls._secret_key_path().open(mode="rb") as f:
            return f.read().strip()

    @classmethod
    def _secret_key(cls, passphrase: bytes, salt: bytes) -> bytes:
        """Build some secret for the encryption

        Use the sites auth.secret for encryption. This secret is only known to the current site
        and other distributed sites.
        """
        return hashlib.scrypt(passphrase, salt=salt, n=2**14, r=8, p=1, dklen=32)

    @classmethod
    def _cipher(cls, key: bytes, nonce: bytes):
        return AES.new(key, AES.MODE_GCM, nonce=nonce)

    @classmethod
    def encrypt(cls, value: str) -> bytes:
        salt = os.urandom(AES.block_size)
        nonce = os.urandom(AES.block_size)
        cipher = cls._cipher(cls._secret_key(cls._passphrase(), salt), nonce)
        encrypted, tag = cipher.encrypt_and_digest(value.encode("utf-8"))
        return salt + nonce + tag + encrypted

    @classmethod
    def decrypt(cls, raw: bytes) -> str:
        salt, rest = raw[: AES.block_size], raw[AES.block_size :]
        nonce, rest = rest[: AES.block_size], rest[AES.block_size :]
        tag, encrypted = rest[: AES.block_size], rest[AES.block_size :]

        return (
            cls._cipher(cls._secret_key(cls._passphrase(), salt), nonce)
            .decrypt_and_verify(encrypted, tag)
            .decode("utf-8")
        )

#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from tests.testlib.certs import rsa_private_keys_equal

from cmk.utils.crypto.keys import (
    InvalidSignatureError,
    PlaintextPrivateKeyPEM,
    PrivateKey,
    PublicKey,
    PublicKeyPEM,
    WrongPasswordError,
)
from cmk.utils.crypto.password import Password
from cmk.utils.crypto.types import HashAlgorithm, InvalidPEMError, Signature


def test_serialize_rsa_key(tmp_path: Path, rsa_key: PrivateKey) -> None:
    pem_plain = rsa_key.dump_pem(None)
    assert pem_plain.str.startswith("-----BEGIN PRIVATE KEY-----")

    loaded_plain = PrivateKey.load_pem(pem_plain)
    assert rsa_private_keys_equal(loaded_plain, rsa_key)

    pem_enc = rsa_key.dump_pem(Password("verysecure"))
    assert pem_enc.str.startswith("-----BEGIN ENCRYPTED PRIVATE KEY-----")

    with pytest.raises((WrongPasswordError, InvalidPEMError)):
        # This should really be a WrongPasswordError, but for some reason we see an InvalidPEMError
        # instead. We're not sure if it's an issue of our unit tests or if this confusion can also
        # happen in production. See also `PrivateKey.load_pem()`.
        PrivateKey.load_pem(pem_enc, Password("wrong"))

    loaded_enc = PrivateKey.load_pem(pem_enc, Password("verysecure"))
    assert rsa_private_keys_equal(loaded_enc, rsa_key)

    pem_pkcs1 = rsa_key.dump_legacy_pkcs1()
    assert pem_pkcs1.str.startswith("-----BEGIN RSA PRIVATE KEY-----")

    pubkey_pem = rsa_key.public_key.dump_pem()
    assert pubkey_pem.str.startswith("-----BEGIN RSA PUBLIC KEY-----")

    pubkey_openssh = rsa_key.public_key.dump_openssh()
    assert pubkey_openssh.startswith("ssh-rsa ")


@pytest.mark.parametrize("data", [b"", b"test", b"\0\0\0", "sign here: 📝".encode()])
def test_verify_rsa_key(data: bytes, rsa_key: PrivateKey) -> None:
    signed = rsa_key.rsa_sign_data(data)

    rsa_key.public_key.rsa_verify(signed, data, HashAlgorithm.Sha512)

    with pytest.raises(InvalidSignatureError):
        rsa_key.public_key.rsa_verify(Signature(b"nope"), data, HashAlgorithm.Sha512)


def test_load_pem_unsupported_key() -> None:
    # openssl genpkey -algorithm x448
    x448_priv_pem = PlaintextPrivateKeyPEM(
        """
-----BEGIN PRIVATE KEY-----
MEYCAQAwBQYDK2VvBDoEOOA78oJPraLcyLq+tn3QJ7Jk3lwk7V2JYVu2GZ/30vzk
sv5jIhB2eY4i4iYP5I+zJs27OGfYmdjU
-----END PRIVATE KEY-----"""
    )

    with pytest.raises(ValueError, match="Unsupported private key"):
        PrivateKey.load_pem(x448_priv_pem)

    # openssl pkey -pubout -outform PEM
    x448_pub_pem = PublicKeyPEM(
        """
-----BEGIN PUBLIC KEY-----
MEIwBQYDK2VvAzkAr/nD2Idiuxtr/BS4A7YPTIapVAfEPRe18MQQoNn7eYBdL16K
MUDX2EQBpifAq+lisxq3F+sqr/o=
-----END PUBLIC KEY-----"""
    )

    with pytest.raises(ValueError, match="Unsupported public key"):
        PublicKey.load_pem(x448_pub_pem)

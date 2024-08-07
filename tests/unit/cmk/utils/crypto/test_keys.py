#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.crypto.keys import (
    InvalidSignatureError,
    PlaintextPrivateKeyPEM,
    PrivateKey,
    PublicKey,
    PublicKeyPEM,
    WrongPasswordError,
)
from cmk.utils.crypto.password import Password
from cmk.utils.crypto.types import HashAlgorithm, PEMDecodingError, Signature


@pytest.mark.parametrize(
    "private_key_fixture,expected_openssh_fmt",
    [
        ("ed25519_private_key", "ssh-ed25519 AAAA"),
        ("secp256k1_private_key", "ecdsa-sha2-nistp256 AAAA"),
        ("rsa_private_key", "ssh-rsa AAAA"),
    ],
)
def test_de_serialization(
    private_key_fixture: str,
    expected_openssh_fmt: str,
    request: pytest.FixtureRequest,
) -> None:
    pem = request.getfixturevalue(private_key_fixture)

    # --- private key ---
    private_key = PrivateKey.load_pem(pem)

    assert private_key.dump_pem(None).str == pem.str

    encrypted_pem = private_key.dump_pem(Password("verysecure"))
    assert encrypted_pem.str.startswith("-----BEGIN ENCRYPTED PRIVATE KEY-----")

    with pytest.raises((WrongPasswordError, PEMDecodingError)):
        # This should really be a WrongPasswordError, but for some reason we see an PEMDecodingError
        # instead. We're not sure if it's an issue of our unit tests or if this confusion can also
        # happen in production. See also `PrivateKey.load_pem()`.
        PrivateKey.load_pem(encrypted_pem, Password("wrong"))

    decrypted_private_key = PrivateKey.load_pem(encrypted_pem, Password("verysecure"))
    # __eq__ for private keys is not implemented (nor needed elsewhere), so we check the public keys
    assert decrypted_private_key.public_key == private_key.public_key

    try:
        # only works for RSA keys -- provoke the exception and just pass on other keys
        private_key.get_raw_rsa_key()
    except ValueError:
        pass
    else:
        assert private_key.rsa_dump_legacy_pkcs1().str.startswith("-----BEGIN RSA PRIVATE KEY-----")

    # --- public key ---
    public_key = PrivateKey.load_pem(pem).public_key

    assert public_key.dump_pem().str.startswith("-----BEGIN PUBLIC KEY-----")
    assert public_key.dump_openssh().startswith(expected_openssh_fmt)


@pytest.mark.parametrize("data", [b"", b"test", b"\0\0\0", "sign here: 📝".encode()])
def test_verify_rsa_key(data: bytes, rsa_private_key: PlaintextPrivateKeyPEM) -> None:
    rsa_key = PrivateKey.load_pem(rsa_private_key)
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

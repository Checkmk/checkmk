#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for public / private keys"""

import pytest

from cmk.crypto.hash import HashAlgorithm
from cmk.crypto.keys import (
    InvalidSignatureError,
    PlaintextPrivateKeyPEM,
    PrivateKey,
    PublicKey,
    PublicKeyPEM,
    Signature,
)
from cmk.crypto.password import Password
from cmk.crypto.pem import PEMDecodingError


@pytest.fixture(name="rsa_private_key", scope="module")
def fixture_rsa_private_key() -> PlaintextPrivateKeyPEM:
    # openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:1024
    return PlaintextPrivateKeyPEM(
        """-----BEGIN PRIVATE KEY-----
MIICeAIBADANBgkqhkiG9w0BAQEFAASCAmIwggJeAgEAAoGBALV1mKMO/Md5BsM7
JI1PGvYdbO+qlgVQ1xni8v1kLGv94e32HRfCKf0heVI3lkJi4qdXRcQOP6dzr/u0
ZtgesLJIKwAX/2w47vT4PdMliSeYDKHGfrakvk9xlbGr+jxYviRJx0NJpIZR6pjW
nYdP2O5QakUa2/6XsIBTDtE9b7crAgMBAAECgYEAqnV5mVNu6gMq8yMPxx7UePZT
ayCYJQ43wj2LfbUodZndLqjP04212/AiA7XsFRjHSeOVygKIkUj/vDdPlR3fZUVH
WHzdCnBhMiQzz7XGIO06mkgjpJVkxSy5Ob8moapzucJAZRZNdxcpZZOquJHyCqAo
Hr1oedZ2udvAWxosDIECQQDhWu06JGik2uhoiUIiExNbBTylsMsPUlqsX5eJzVJU
69POK+Y6coJNlOgLTipQrdKUNeoHHrBCbdnw6luQUbIxAkEAziKRBx2qa0uknYTy
PnfDr92hoME555VlJ2t3qOso+7to5Fpp/RrGAZJU8RljTETBE13+NUqsf1b5Z84a
+2msGwJBAMpK4xUEReNmlqXwQKtx0DgutUhPMZjpZnfBv7h11Whh4dn7Uko5LHsU
JlCvtBCEWLmuxAvsInEfRzqaReOBUqECQQCXDqmsx0aNnj8h170VnfpfNFEvVqoy
VT5tZsmnlbzQzIOPY9prymTz3eI1VF96EqBSqvyQ3QoPvxLByT3oo4WlAkBJm0f4
Jf8ojkhcjV5Nqk1rHKBxr2FuvR3u9oAoiOvg5bZ9gtUFJzgU1P6dnwrfvepJJyK2
fCP26dGEODI0TDgM
-----END PRIVATE KEY-----
"""
    )


@pytest.fixture(name="ed25519_private_key", scope="module")
def fixture_ed25519_private_key() -> PlaintextPrivateKeyPEM:
    # openssl genpkey -algorithm Ed25519
    return PlaintextPrivateKeyPEM(
        """-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIPhi2Ui8zfyHhfsPYpsdv9oKd+plPXkFjlgTCnMMbHaR
-----END PRIVATE KEY-----
"""
    )


@pytest.fixture(name="secp256k1_private_key", scope="module")
def fixture_secp256k1_private_key() -> PlaintextPrivateKeyPEM:
    # openssl ecparam -name prime256v1 -genkey | openssl pkcs8 -topk8 -nocrypt
    return PlaintextPrivateKeyPEM(
        """-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgN/NMXDhBlntMLzN/
4z+usHyn6zZMQqGohG0lqm03hnShRANCAARHBsjyc39qc+foF1ZbU7lqM5X2VkMu
RyG9V7BoZNR2t7aqZ/ab551SpZc3t6hj9xnIa/1+2mXAmNEqH920LpWM
-----END PRIVATE KEY-----
"""
    )


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

    with pytest.raises(PEMDecodingError):
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

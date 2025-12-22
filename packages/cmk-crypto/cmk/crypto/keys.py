#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Public and private key types for asymmetric cryptography"""

from __future__ import annotations

from typing import assert_never, get_args, NewType, overload, override, TypeAlias, TypeGuard

import cryptography.exceptions
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed448, ed25519, padding, rsa, types

from . import MKCryptoException
from .hash import HashAlgorithm
from .password import Password
from .pem import _PEMData, PEMDecodingError


class InvalidSignatureError(MKCryptoException):
    """A signature could not be verified"""


class PlaintextPrivateKeyPEM(_PEMData):
    """A unencrypted private key in pem format"""


class EncryptedPrivateKeyPEM(_PEMData):
    """A encrypted private key in pem format"""


class PublicKeyPEM(_PEMData):
    """A public key in pem format"""


Signature = NewType("Signature", bytes)


PublicKeyType: TypeAlias = (
    ed25519.Ed25519PublicKey | ed448.Ed448PublicKey | rsa.RSAPublicKey | ec.EllipticCurvePublicKey
)


def is_supported_public_key_type(key: types.PublicKeyTypes) -> TypeGuard[PublicKeyType]:
    # get_args is a workaround for mypy bug https://github.com/python/mypy/issues/12155
    return isinstance(key, get_args(PublicKeyType))


PrivateKeyType: TypeAlias = (
    ed25519.Ed25519PrivateKey
    | ed448.Ed448PrivateKey
    | rsa.RSAPrivateKey
    | ec.EllipticCurvePrivateKey
)


def is_supported_private_key_type(key: types.PrivateKeyTypes) -> TypeGuard[PrivateKeyType]:
    # get_args is a workaround for mypy bug https://github.com/python/mypy/issues/12155
    return isinstance(key, get_args(PrivateKeyType))


class PrivateKey:
    """
    A private key. Not every kind of private key is supported.

    Supported private key types are:
     - RSA, DSA, Ed25519, Ed448, and EC private keys that can be used with ECDSA
       ("EllipticCurvePrivateKey").
    This list corresponds to CertificateIssuerPrivateKeyTypes in cryptography.

    Not supported are keys types that can only be used for key exchange (DH, x25519, x448), due to
    the lack of a use-case.
    """

    def __init__(self, key: PrivateKeyType) -> None:
        self._key = key

    @classmethod
    def generate_rsa(cls, key_size: int) -> PrivateKey:
        return cls(rsa.generate_private_key(public_exponent=65537, key_size=key_size))

    @overload
    @classmethod
    def load_pem(cls, pem_data: PlaintextPrivateKeyPEM, password: None = None) -> PrivateKey: ...

    @overload
    @classmethod
    def load_pem(cls, pem_data: EncryptedPrivateKeyPEM, password: Password) -> PrivateKey: ...

    @classmethod
    def load_pem(
        cls,
        pem_data: EncryptedPrivateKeyPEM | PlaintextPrivateKeyPEM,
        password: Password | None = None,
    ) -> PrivateKey:
        """
        Decode a PKCS8 PEM encoded RSA private key.

        `password` can be given if the key is encrypted.

        Raises:
            PEMDecodingError: if the PEM cannot be decoded or decrypted.
            ValueError: if the decoded key type is not supported.
        """

        pw = password.raw_bytes if password is not None else None
        try:
            key = serialization.load_pem_private_key(pem_data.bytes, password=pw)

        except ValueError as exc:
            raise PEMDecodingError("Invalid PEM or wrong password") from exc

        if not is_supported_private_key_type(key):
            # We support only key types that can be used to for signatures. See class docstring.
            raise ValueError(f"Unsupported private key type {type(key)}")

        return cls(key)

    @overload
    def dump_pem(self, password: None) -> PlaintextPrivateKeyPEM: ...

    @overload
    def dump_pem(self, password: Password) -> EncryptedPrivateKeyPEM: ...

    def dump_pem(
        self, password: Password | None
    ) -> EncryptedPrivateKeyPEM | PlaintextPrivateKeyPEM:
        """
        Encode the private key in PKCS8 PEM (i.e. '-----BEGIN PRIVATE KEY-----...').

        If `password` is given, the key will be encrypted with the password
        (i.e. '-----BEGIN ENCRYPTED PRIVATE KEY-----...').
        """

        bytes_ = self._key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=(
                serialization.BestAvailableEncryption(password.raw_bytes)
                if password is not None
                else serialization.NoEncryption()
            ),
        )
        if password is None:
            return PlaintextPrivateKeyPEM(bytes_)
        return EncryptedPrivateKeyPEM(bytes_)

    def rsa_dump_legacy_pkcs1(self) -> PlaintextPrivateKeyPEM:
        """Deprecated. Use dump_pem() instead.

        This method only works on RSA keys!

        Encode the private key without encryption in PKCS#1 / OpenSSL format
        (i.e. '-----BEGIN RSA PRIVATE KEY-----...').
        """
        bytes_ = self.get_raw_rsa_key().private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return PlaintextPrivateKeyPEM(bytes_)

    @property
    def public_key(self) -> PublicKey:
        return PublicKey(self._key.public_key())

    def get_raw_rsa_key(self) -> rsa.RSAPrivateKey:
        """
        Get the raw underlying key IF it is an RSA key. Raise a ValueError otherwise.

        This should be avoided, but can be useful in situations where other key types are not
        supported yet.
        """
        if not isinstance(self._key, rsa.RSAPrivateKey):
            raise ValueError("Not an RSA private key")

        return self._key

    def rsa_sign_data(
        self, data: bytes, hash_algorithm: HashAlgorithm = HashAlgorithm.Sha512
    ) -> Signature:
        """
        Assert an RSA key and create a signature.

        PKCS1v15 padding will be used. If the underlying key is not an RSA key, a ValueError is
        raised.
        """
        return Signature(
            self.get_raw_rsa_key().sign(data, padding.PKCS1v15(), hash_algorithm.value)
        )


class PublicKey:
    """
    A public key. Not every kind of public key is supported.

    Supported public key types are:
     - RSA, DSA, Ed25519, Ed448, and EC public keys that can be used with ECDSA
       ("EllipticCurvePublicKey").
    This list corresponds to CertificateIssuerPublicKeyTypes in cryptography.

    Not supported are keys types that can only be used for key exchange (DH, x25519, x448), due to
    the lack of a use-case.
    """

    def __init__(self, key: PublicKeyType) -> None:
        self._key = key

    @property
    def key(self) -> PublicKeyType:
        return self._key

    @classmethod
    def load_pem(cls, pem_data: PublicKeyPEM) -> PublicKey:
        key = serialization.load_pem_public_key(pem_data.bytes)

        if not is_supported_public_key_type(key):
            # We support only key types that can be used to for signatures. See class docstring.
            raise ValueError(f"Unsupported public key type {type(key)}")

        return cls(key)

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PublicKey):
            return NotImplemented
        return self._key == other._key

    def dump_pem(self) -> PublicKeyPEM:
        return PublicKeyPEM(
            self._key.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

    def dump_openssh(self) -> str:
        """Encode the public key in OpenSSH format (ssh-rsa AAAA...)"""
        return self._key.public_bytes(
            serialization.Encoding.OpenSSH,
            serialization.PublicFormat.OpenSSH,
        ).decode("utf-8")

    def get_raw_rsa_key(self) -> rsa.RSAPublicKey:
        """
        Get the raw underlying key IF it is an RSA key. Raise a ValueError otherwise.

        This should be avoided, but can be useful in situations where other key types are not
        supported yet.
        """
        if not isinstance(self._key, rsa.RSAPublicKey):
            raise ValueError("Not an RSA public key")

        return self._key

    def rsa_verify(
        self, signature: Signature, message: bytes, digest_algorithm: HashAlgorithm
    ) -> None:
        """
        Assert an RSA key and verify a signature.

        PKCS1v15 padding is assumed. If the underlying key is not an RSA key, a ValueError is
        raised.
        """
        try:
            self.get_raw_rsa_key().verify(
                signature, message, padding.PKCS1v15(), digest_algorithm.value
            )
        except cryptography.exceptions.InvalidSignature as e:
            raise InvalidSignatureError(e) from e

    def show_type(self) -> str:
        match self._key:
            case ed25519.Ed25519PublicKey():
                return "Ed25519"
            case ed448.Ed448PublicKey():
                return "Ed448"
            case rsa.RSAPublicKey():
                return f"RSA {self._key.key_size} bits"
            case ec.EllipticCurvePublicKey():
                return f"EC {self._key.curve.name}"
            case _:
                assert_never(self._key)

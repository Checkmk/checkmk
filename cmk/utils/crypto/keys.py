#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import get_args, overload, TypeAlias, TypeGuard

import cryptography.exceptions
import cryptography.hazmat.primitives.asymmetric as asym
import cryptography.hazmat.primitives.asymmetric.padding as padding
from cryptography.hazmat.primitives import serialization

from cmk.utils.crypto.password import Password
from cmk.utils.crypto.types import (
    HashAlgorithm,
    InvalidPEMError,
    MKCryptoException,
    SerializedPEM,
    Signature,
)


class WrongPasswordError(MKCryptoException):
    """The private key could not be decrypted, probably due to a wrong password"""


class InvalidSignatureError(MKCryptoException):
    """A signature could not be verified"""


class PlaintextPrivateKeyPEM(SerializedPEM):
    """A unencrypted private key in pem format"""


class EncryptedPrivateKeyPEM(SerializedPEM):
    """A encrypted private key in pem format"""


class PublicKeyPEM(SerializedPEM):
    """A public key in pem format"""


PublicKeyType: TypeAlias = (
    asym.ed25519.Ed25519PublicKey
    | asym.ed448.Ed448PublicKey
    | asym.rsa.RSAPublicKey
    | asym.ec.EllipticCurvePublicKey
)


def is_supported_public_key_type(key: asym.types.PublicKeyTypes) -> TypeGuard[PublicKeyType]:
    # get_args is a workaround for mypy bug https://github.com/python/mypy/issues/12155
    return isinstance(key, get_args(PublicKeyType))


PrivateKeyType: TypeAlias = (
    asym.ed25519.Ed25519PrivateKey
    | asym.ed448.Ed448PrivateKey
    | asym.rsa.RSAPrivateKey
    | asym.ec.EllipticCurvePrivateKey
)


def is_supported_private_key_type(key: asym.types.PrivateKeyTypes) -> TypeGuard[PrivateKeyType]:
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
        return cls(asym.rsa.generate_private_key(public_exponent=65537, key_size=key_size))

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
            InvalidPEMError: if the PEM cannot be decoded.
            WrongPasswordError: if an encrypted PEM cannot be decrypted with the given password.
                NOTE: it seems we cannot rely on this error being raised. In the unit tests we
                sometimes saw an InvalidPEMError instead. Expect to see that as well.
            TypeError: when trying to load an EncryptedPrivateKeyPEM but no password is given.
                This would be caught by mypy though.

        >>> PrivateKey.load_pem(EncryptedPrivateKeyPEM(""))
        Traceback (most recent call last):
            ...
        cmk.utils.crypto.types.InvalidPEMError

        >>> pem = EncryptedPrivateKeyPEM(
        ...     "\\n".join([
        ...         "-----BEGIN ENCRYPTED PRIVATE KEY-----",
        ...         "MIIC3TBXBgkqhkiG9w0BBQ0wSjApBgkqhkiG9w0BBQwwHAQIMRfolchikB0CAggA",
        ...         "MAwGCCqGSIb3DQIJBQAwHQYJYIZIAWUDBAEqBBBvZ2ZdTgc5U+OgzNvBs3cXBIIC",
        ...         "gBe7tt6aHu+sfCvU8EzFqVbkf3f3qt6P/YEJZu4zXeGXrE+4D7E64PYooqGk+ZvU",
        ...         "/xyqHNoRzbAGEAqqEsMhZxjhQbgLmWVqGCJrqkkl8d5UlcG661AuevhYqIW8D3Bk",
        ...         "PfezIOnL+tDJuNb8y3KgQU0mqjUZ/BFLy6uTm6hQWeBluU5xtJ3C59o2JCP3pQwz",
        ...         "5V/EuLu0nLRSxCxDGcZqCr0s5A0AGv4U7xA9LEgER+ZuXLa2m+zp8VI8aR+1zUp+",
        ...         "lWq4rFY2UnA3DNayS/5QV0ljgDbE8Bzje6dwDhRiFUhgIwHa4C6EEDTajAXxbJEz",
        ...         "JebDaz9HLUMbfFdE2LYjagQx/kopb35eZUihZs3uHZXgXCQzeaaG7bunPBdiCuML",
        ...         "n0Cg+h13PmuH4eXuzcLEvwGzJrBrhenuYs/Vp9PYhwI7gIq+pqx7cgBprOge4xqM",
        ...         "gZbyhYoWCITEMg6lMYga1uZuBtvkel7/0PtC35qxdJyo5AEUCwSisY//t7oZownH",
        ...         "e8RlioxKnCisNxtcMYkPLmU68HNklZSX4/FrSd9zrWrpxC9XKKYeixe/RZPApeXO",
        ...         "phVLXl8KaX/xEAuonEZXH9XaZRnYA1Lg4Hl3lfbbHVffet9X1jpRRo4RCuQ+yQrJ",
        ...         "+YvX8SvnNAYHB1Pfp6aEqauUBR6FisUhHx2xahvnJ8y1GFNwY1VUEDdB63Ai0JVK",
        ...         "zIzEXU8/psX8xDh5Gm+n4ZVkgbuJQdvQgYLNT6vEglytEuJXYKFZQY4zX8J+vc3N",
        ...         "AVqHeoR61JEG+AcMdUgg2bO3vYorcQ8b3kwKkZzoBNeghMl6IS0Lj5tLVixweS5d",
        ...         "Rnp7GPpozA4jOM89/WEk+LE=",
        ...         "-----END ENCRYPTED PRIVATE KEY-----"
        ...     ])
        ... )

        >>> PrivateKey.load_pem(pem, Password("foo"))
        <cmk.utils.crypto.keys.PrivateKey object at 0x...>

        >>> PrivateKey.load_pem(pem, Password("not foo"))
        Traceback (most recent call last):
            ...
        cmk.utils.crypto.keys.WrongPasswordError
        """

        pw = password.raw_bytes if password is not None else None
        try:
            key = serialization.load_pem_private_key(pem_data.bytes, password=pw)

        except ValueError as exception:
            if str(exception) == "Bad decrypt. Incorrect password?":
                raise WrongPasswordError
            raise InvalidPEMError

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

    def get_raw_rsa_key(self) -> asym.rsa.RSAPrivateKey:
        """
        Get the raw underlying key IF it is an RSA key. Raise a ValueError otherwise.

        This should be avoided, but can be useful in situations where other key types are not
        supported yet.
        """
        if not isinstance(self._key, asym.rsa.RSAPrivateKey):
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

    @classmethod
    def load_pem(cls, pem_data: PublicKeyPEM) -> PublicKey:
        key = serialization.load_pem_public_key(pem_data.bytes)

        if not is_supported_public_key_type(key):
            # We support only key types that can be used to for signatures. See class docstring.
            raise ValueError(f"Unsupported public key type {type(key)}")

        return cls(key)

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

    def get_raw_rsa_key(self) -> asym.rsa.RSAPublicKey:
        """
        Get the raw underlying key IF it is an RSA key. Raise a ValueError otherwise.

        This should be avoided, but can be useful in situations where other key types are not
        supported yet.
        """
        if not isinstance(self._key, asym.rsa.RSAPublicKey):
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
                signature, message, asym.padding.PKCS1v15(), digest_algorithm.value
            )
        except cryptography.exceptions.InvalidSignature as e:
            raise InvalidSignatureError(e) from e

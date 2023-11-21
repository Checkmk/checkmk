#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import overload

import cryptography.exceptions
import cryptography.hazmat.primitives.asymmetric.padding as padding
import cryptography.hazmat.primitives.asymmetric.rsa as rsa
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


class PrivateKey:
    """
    An unencrypted RSA private key.

    This class provides methods to generate, serialize and deserialize RSA private keys.
    """

    def __init__(self, key: rsa.RSAPrivateKey) -> None:
        self._key = key

    @classmethod
    def generate_rsa(cls, key_size: int) -> PrivateKey:
        return cls(rsa.generate_private_key(public_exponent=65537, key_size=key_size))

    @overload
    @classmethod
    def load_pem(cls, pem_data: PlaintextPrivateKeyPEM, password: None = None) -> PrivateKey:
        ...

    @overload
    @classmethod
    def load_pem(cls, pem_data: EncryptedPrivateKeyPEM, password: Password) -> PrivateKey:
        ...

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
            deserialized = serialization.load_pem_private_key(pem_data.bytes, password=pw)
            assert isinstance(deserialized, rsa.RSAPrivateKey)
            return PrivateKey(deserialized)
        except ValueError as exception:
            if str(exception) == "Bad decrypt. Incorrect password?":
                raise WrongPasswordError
            raise InvalidPEMError

    @overload
    def dump_pem(self, password: None) -> PlaintextPrivateKeyPEM:
        ...

    @overload
    def dump_pem(self, password: Password) -> EncryptedPrivateKeyPEM:
        ...

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
            encryption_algorithm=serialization.BestAvailableEncryption(password.raw_bytes)
            if password is not None
            else serialization.NoEncryption(),
        )
        if password is None:
            return PlaintextPrivateKeyPEM(bytes_)
        return EncryptedPrivateKeyPEM(bytes_)

    def dump_legacy_pkcs1(self) -> PlaintextPrivateKeyPEM:
        """Deprecated. Do not use.

        Encode the private key without encryption in PKCS#1 / OpenSSL format
        (i.e. '-----BEGIN RSA PRIVATE KEY-----...').
        """
        bytes_ = self._key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return PlaintextPrivateKeyPEM(bytes_)

    @property
    def public_key(self) -> PublicKey:
        return PublicKey(self._key.public_key())

    def sign_data(
        self, data: bytes, hash_algorithm: HashAlgorithm = HashAlgorithm.Sha512
    ) -> Signature:
        return Signature(self._key.sign(data, padding.PKCS1v15(), hash_algorithm.value))


class PublicKey:
    def __init__(self, key: rsa.RSAPublicKey) -> None:
        self._key = key

    @classmethod
    def load_pem(cls, pem_data: PublicKeyPEM) -> PublicKey:
        deserialized = serialization.load_pem_public_key(pem_data.bytes)
        assert isinstance(deserialized, rsa.RSAPublicKey)
        return PublicKey(deserialized)

    def dump_pem(self) -> PublicKeyPEM:
        # TODO: Use SubjectPublicKeyInfo format rather than PKCS1. PKCS1 doesn't include an
        # algorithm identifier.
        return PublicKeyPEM(
            self._key.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.PKCS1,
            )
        )

    def dump_openssh(self) -> str:
        """Encode the public key in OpenSSH format (ssh-rsa AAAA...)"""
        return self._key.public_bytes(
            serialization.Encoding.OpenSSH,
            serialization.PublicFormat.OpenSSH,
        ).decode("utf-8")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PublicKey):
            return NotImplemented
        return self._key.public_numbers() == other._key.public_numbers()

    def verify(self, signature: Signature, message: bytes, digest_algorithm: HashAlgorithm) -> None:
        # Currently the discouraged PKCS1 v1.5 padding is assumed. This is the only padding scheme
        # cryptography.io supports for signing X.509 certificates at this time.
        # See https://github.com/pyca/cryptography/issues/2850.
        # As long as our RsaPublic/PrivateKeys are only used for certificates there's no point in
        # supporting other schemes.
        padding_scheme = padding.PKCS1v15()

        try:
            self._key.verify(signature, message, padding_scheme, digest_algorithm.value)
        except cryptography.exceptions.InvalidSignature as e:
            raise InvalidSignatureError(e) from e

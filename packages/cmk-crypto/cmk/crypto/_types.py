#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Types and exceptions for the crypto pacakge"""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import NewType

from cryptography.hazmat.primitives import hashes as crypto_hashes


class HashAlgorithm(Enum):
    """This is just a facade to selected hash algorithms from cryptography"""

    MD5 = crypto_hashes.MD5()  # nosec B303 # BNS:e9bfaa
    Sha1 = crypto_hashes.SHA1()  # pylint: disable=invalid-name # nosec B303 # BNS:02774b
    Sha256 = crypto_hashes.SHA256()  # pylint: disable=invalid-name
    Sha384 = crypto_hashes.SHA384()  # pylint: disable=invalid-name
    Sha512 = crypto_hashes.SHA512()  # pylint: disable=invalid-name

    @classmethod
    def from_cryptography(cls, algo: crypto_hashes.HashAlgorithm) -> HashAlgorithm:
        match algo:
            case crypto_hashes.SHA256():
                return HashAlgorithm.Sha256
            case crypto_hashes.SHA384():
                return HashAlgorithm.Sha384
            case crypto_hashes.SHA512():
                return HashAlgorithm.Sha512
        raise ValueError(f"Unsupported hash algorithm: '{algo.name}'")

    def to_hashlib(self) -> hashlib._Hash:
        match self.value:
            case crypto_hashes.SHA1():
                return hashlib.new("sha1")  # nosec B324 # BNS:eb967b
        raise ValueError(f"Unsupported hash algorithm: '{self.value.name}'")


Signature = NewType("Signature", bytes)


class SerializedPEM:
    """A serialized anything in PEM format

    we tried NewTypes but the str or bytes encoding/decoding calls were just
    annoying. This class can be inherited by the former NewTypes"""

    def __init__(self, pem: str | bytes) -> None:
        if isinstance(pem, str):
            self._data = pem.encode()
        elif isinstance(pem, bytes):
            self._data = pem
        else:
            raise TypeError("Pem must either be bytes or str")

    @property
    def str(self) -> str:
        return self._data.decode()

    @property
    def bytes(self) -> bytes:
        return self._data


class MKCryptoException(Exception):
    """Common baseclass for this module's exceptions"""


class PEMDecodingError(MKCryptoException):
    """Decoding a PEM has failed.

    Possible reasons:
     - PEM structure is invalid
     - decoded content is not as expected
     - PEM is encrypted and the password is wrong
    """

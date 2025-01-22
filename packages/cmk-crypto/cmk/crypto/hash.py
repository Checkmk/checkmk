#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Hash algorithms"""

from __future__ import annotations

import hashlib
from enum import Enum

from cryptography.hazmat.primitives import hashes as crypto_hashes


class HashAlgorithm(Enum):
    """This is just a facade to selected hash algorithms from cryptography"""

    MD5 = crypto_hashes.MD5()  # nosec B303 # BNS:e9bfaa
    Sha1 = crypto_hashes.SHA1()  # nosec B303 # BNS:02774b
    Sha256 = crypto_hashes.SHA256()
    Sha384 = crypto_hashes.SHA384()
    Sha512 = crypto_hashes.SHA512()

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

#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This package contains cryptographic functionality for Checkmk.

It aims to provide a coherent, hard-to-misuse API. It should also serve as a facade to both
our crypto dependencies and python's built-in crypto utilities (like hashlib).
"""
from __future__ import annotations

from enum import Enum

from cryptography.hazmat.primitives import hashes as crypto_hashes


class HashAlgorithm(Enum):
    """This is just a facade to selected hash algorithms from cryptography"""

    # TODO: burn it...
    MD5 = crypto_hashes.MD5()  # nosec
    Sha1 = crypto_hashes.SHA1()  # nosec
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

#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Low-lever utilities for symmetric cryptography"""

from dataclasses import dataclass
from typing import ClassVar

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass
class TaggedCiphertext:
    """A ciphertext with an AEAD tag appended.

    This is just a helper class to abstract from the order of ciphertext and tag,
    which unfortunately is different in our containers and pyca/cryptography.

    The tag is assumed to be 16 bytes long.
    """

    TAG_LENGTH: ClassVar[int] = 16

    ciphertext: bytes
    tag: bytes


def aes_gcm_encrypt(key: bytes, nonce: bytes, plaintext: str) -> TaggedCiphertext:
    encrypted = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
    return TaggedCiphertext(
        ciphertext=encrypted[: -TaggedCiphertext.TAG_LENGTH],
        tag=encrypted[-TaggedCiphertext.TAG_LENGTH :],
    )


def aes_gcm_decrypt(key: bytes, nonce: bytes, ciphertext: TaggedCiphertext) -> str:
    return (
        AESGCM(key)
        .decrypt(nonce, ciphertext.ciphertext + ciphertext.tag, associated_data=None)
        .decode("utf-8")
    )

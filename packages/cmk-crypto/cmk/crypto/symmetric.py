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
    """Symmetrically encrypt a plaintext given a key and a nonce.

    AES GCM is an "authenticated encryption with associated data (AEAD)" mode. This means that MAC
    calculation, i.e. verification that the message has not been altered, is included in the
    encryption scheme.

    Args:
        key: The key can be 16, 24, or 32 bytes long. Note that a password or human-readable random
        characters are not suitable as key material. The key should be either generated randomly
        (e.g. using `secrets.token_bytes()`), or derived from a password with a key derivation
        function like argon2id.

        nonce: The nonce (number used once) should be 16 bytes long. It MUST NEVER be re-used.
        Obtain it by generating 16 random bytes and transfer it together with the cipher text. The
        nonce is not secret.

        plaintext: The plaintext to be encrypted.

    Returns:
        The ciphertext and the tag, which is used to authenticate the message. Both values need to
        be transferred and provided to the decryption function in the same order.
    """
    encrypted = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
    return TaggedCiphertext(
        ciphertext=encrypted[: -TaggedCiphertext.TAG_LENGTH],
        tag=encrypted[-TaggedCiphertext.TAG_LENGTH :],
    )


def aes_gcm_decrypt(key: bytes, nonce: bytes, ciphertext: TaggedCiphertext) -> str:
    """Decrypt a ciphertext given a key and a nonce.

    This is the inverse method for `aes_gcm_encrypt`. See the docstring of `aes_gcm_encrypt` for
    further information.
    """
    return (
        AESGCM(key)
        .decrypt(nonce, ciphertext.ciphertext + ciphertext.tag, associated_data=None)
        .decode("utf-8")
    )

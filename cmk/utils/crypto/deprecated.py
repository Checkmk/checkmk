#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Deprecated crypto utilities that should not be used in new code"""

from typing import Literal, TypeAlias

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import algorithms, Cipher, modes

import cmk.utils.crypto.certificate as certificate
from cmk.utils.crypto import HashAlgorithm

_Buffer: TypeAlias = bytes | bytearray | memoryview


class AesCbcCipher:
    """Deprecated. Do not use."""

    BLOCK_SIZE = 16

    def __init__(self, mode: Literal["encrypt", "decrypt"], key: bytes, iv: bytes):
        self._cipher = (
            Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
            if mode == "encrypt"
            else Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
        )

    def update(self, data: bytes) -> bytes:
        return self._cipher.update(data)

    def finalize(self) -> bytes:
        return self._cipher.finalize()

    @staticmethod
    def pad_block(block: bytes) -> bytes:
        """Add PKCS#7 padding to the block.

        The block is filled to the full BLOCK_SIZE by appending n bytes of value n. If the block is
        empty, a full block of padding bytes is returned.
        """
        padding_length = (
            AesCbcCipher.BLOCK_SIZE - len(block) % AesCbcCipher.BLOCK_SIZE
        ) or AesCbcCipher.BLOCK_SIZE
        return block + padding_length * bytes((padding_length,))

    @staticmethod
    def unpad_block(block: _Buffer) -> _Buffer:
        """Strip PKCS#7 padding from the block."""
        return memoryview(block)[: -block[-1]]


def encrypt_for_rsa_key(recipient_key: certificate.RsaPublicKey, data: bytes) -> bytes:
    """Deprecated. Do not use."""
    return recipient_key._key.encrypt(
        data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=HashAlgorithm.Sha1.value),
            algorithm=HashAlgorithm.Sha1.value,
            label=None,
        ),
    )


def decrypt_with_rsa_key(recipient_key: certificate.RsaPrivateKey, data: bytes) -> bytes:
    """Deprecated. Do not use."""
    return recipient_key._key.decrypt(
        data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=HashAlgorithm.Sha1.value),
            algorithm=HashAlgorithm.Sha1.value,
            label=None,
        ),
    )


def certificate_md5_digest(cert: certificate.Certificate) -> str:
    """Deprecated. Do not use.

    Calculates a digest that corresponds to pyOpenSSL certificate's `.digest("md5")` method.
    """
    return cert.fingerprint(HashAlgorithm.MD5).hex(":").upper()

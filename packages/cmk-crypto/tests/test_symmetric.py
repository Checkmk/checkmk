#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test for symmetric crypto"""

import secrets
from base64 import b64decode

from cmk.crypto.symmetric import aes_gcm_decrypt, aes_gcm_encrypt, TaggedCiphertext


def test_decrypt() -> None:
    ciphertext = b64decode(b"XmzZQpG45A==")
    tag = b64decode(b"SzTMqBrFPmlTvuw6OZYPjQ==")
    key = b64decode(b"Vz8vf4fEoPyXw/nw/uSLeA==")
    nonce = b64decode(b"35ES0UkUa/GGdyVHmgHChg==")

    assert aes_gcm_decrypt(key, nonce, TaggedCiphertext(ciphertext, tag)) == "HI MOM!"


def test_roundtrip() -> None:
    plain = "I refuse to answer that question on the grounds that I don't know the answer."
    key = secrets.token_bytes(16)
    nonce = secrets.token_bytes(16)

    encrypted = aes_gcm_encrypt(key, nonce, plain)
    assert plain == aes_gcm_decrypt(
        key, nonce, TaggedCiphertext(encrypted.ciphertext, encrypted.tag)
    )

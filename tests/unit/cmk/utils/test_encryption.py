#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import hashlib
from binascii import unhexlify

import pytest

from cmk.utils.encryption import decrypt_by_agent_protocol, Encrypter, TransportProtocol


@pytest.mark.skipif(
    not hasattr(hashlib, "scrypt"), reason="OpenSSL version too old, must be >= 1.1"
)
def test_value_encrypter_transparent() -> None:
    assert Encrypter.decrypt(Encrypter.encrypt(data := "abc")) == data


@pytest.mark.parametrize(
    "protocol,encrypted",
    [
        (
            TransportProtocol.PBKDF2,
            # printf "<<<cmk_test>>>" | openssl enc -aes-256-cbc -md sha256 -iter 10000 -k "cmk"
            b"53616c7465645f5f5474944b9c6f675a14a8c05ca120a284c4f04760ad60e8f2",
        ),
        (
            TransportProtocol.SHA256,
            # printf "<<<cmk_test>>>" |  openssl enc -aes-256-cbc -md sha256 -k "cmk" -nosalt
            b"1a6fabbab6d89aeb410d920b04d8f917",
        ),
        (
            TransportProtocol.MD5,
            # printf "<<<cmk_test>>>" | openssl enc -aes-256-cbc -md md5 -k "cmk" -nosalt
            b"0ce5f41d8c9440f8a4291f43110fb025",
        ),
    ],
)
def test_characterization_legacy_encryption(protocol: TransportProtocol, encrypted: bytes) -> None:
    """A characterization test to ensure we can still decrypt the deprecated encrypted agent output"""
    assert decrypt_by_agent_protocol("cmk", protocol, unhexlify(encrypted)) == b"<<<cmk_test>>>"

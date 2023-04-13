#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import hashlib

import pytest

from cmk.utils.encryption import Encrypter


@pytest.mark.skipif(
    not hasattr(hashlib, "scrypt"), reason="OpenSSL version too old, must be >= 1.1"
)
def test_value_encrypter_transparent() -> None:
    assert Encrypter.decrypt(Encrypter.encrypt(data := "abc")) == data

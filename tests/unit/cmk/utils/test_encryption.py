#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import hashlib

import pytest

import cmk.utils.paths
from cmk.utils.encryption import Encrypter


@pytest.fixture()
def fixture_auth_secret():
    secret_path = cmk.utils.paths.omd_root / "etc" / "auth.secret"
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    with secret_path.open("wb") as f:
        f.write(b"auth-secret")


@pytest.mark.skipif(
    not hasattr(hashlib, "scrypt"), reason="OpenSSL version too old, must be >= 1.1"
)
@pytest.mark.usefixtures("fixture_auth_secret")
def test_value_encrypter_transparent() -> None:
    assert Encrypter.decrypt(Encrypter.encrypt(data := "abc")) == data

#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test the secrets"""

from pathlib import Path

from cmk.crypto.secrets import LocalSecret, Secret


def test_create_secret_and_hmac(tmp_path: Path) -> None:
    """A secret can be instantiated and the HMAC comes out as expected"""

    my_secret_file = tmp_path / "mytest.secret"
    my_secret_file.write_bytes(b"my test secret")

    class MySecret(LocalSecret):
        """Mockup"""

        path = my_secret_file

    secret = MySecret()

    assert secret.path == my_secret_file
    assert (
        secret.secret.hmac(b"hello").hex()
        == "3bc5a0f1f479929f6c6330bd2dabf2d78ed389ab329f2c0b0baadfb3a01dbeae"
    )


def test_secret_base64() -> None:
    """Secrets can be converted to and from base64"""

    secret = Secret.generate(length=8)
    assert secret.compare(Secret.from_b64(secret.b64_str))

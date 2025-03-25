#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the TOTP module"""

import math

import pytest

from cmk.crypto.totp import TOTP, TotpVersion

SECRET = b"12345678901234567890"


@pytest.mark.parametrize(
    ["count", "hash_object", "otp"],
    [
        (0, "cc93cf18508d94934c64b65d8ba7667fb7cde4b0", 755224),
        (1, "75a48a19d4cbe100644e8ac1397eea747a2d33ab", 287082),
        (2, "0bacb7fa082fef30782211938bc1c5e70416ff44", 359152),
        (3, "66c28227d03a2d5529262ff016a1e6ef76557ece", 969429),
        (4, "a904c900a64b35909874b33e61c5938a8e15ed1c", 338314),
        (5, "a37e783d7b7233c083d4f62926c7a25f238d0316", 254676),
        (6, "bc9cd28561042c83f219324d3c607256c03272ae", 287922),
        (7, "a4fb960c0bc06e1eabb804e5b397cdc4b45596fa", 162583),
        (8, "1b3c89f65e6c9e883012052823443f048b4332db", 399871),
        (9, "1637409809a679dc698207310c8c7fc07290d9e5", 520489),
    ],
)
def test_hotp(count: int, hash_object: str, otp: int) -> None:
    totp = TOTP(SECRET, TotpVersion.ONE)

    hmac_sha1 = totp._hmac_hash(count)  # noqa: SLF001
    hotp = totp.generate_hotp(hmac_sha1)

    assert hmac_sha1.hexdigest() == hash_object
    assert hotp == otp


@pytest.mark.parametrize(
    ["time", "otp"],
    [
        (59, "94287082"),
        (1111111111, "14050471"),
        (1234567890, "89005924"),
        (1111111109, "07081804"),
        (2000000000, "69279037"),
        (20000000000, "65353130"),
    ],
)
def test_totp_generate(time: int, otp: str) -> None:
    totp = TOTP(SECRET, TotpVersion.RFC6238)

    gen_time = math.floor(time / 30)
    code = totp.generate_totp(gen_time)

    assert code == otp


@pytest.mark.parametrize(
    ["time", "otp"],
    [
        (59, "84755224"),
        (60, "94287082"),
    ],
)
def test_totp_check(time: int, otp: str) -> None:
    totp = TOTP(SECRET, TotpVersion.RFC6238)

    gen_time = math.floor(time / 30)
    status = totp.check_totp(otp, gen_time)

    assert status is True

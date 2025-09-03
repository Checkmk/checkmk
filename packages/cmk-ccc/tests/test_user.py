#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.user import UserId


@pytest.mark.parametrize(
    "user_value",
    [
        "",
        "cmkadmin",
        "$cmk_@dmün.1",
        "$cmkädmin",
        "ↄ𝒽ѥ𝕔𖹬-艋く",
        "cmkadmin@hi.com",
        "cmkadmin+test@hi.com",
    ],
)
def test_valid_user(user_value: str) -> None:
    UserId(user_value)


@pytest.mark.parametrize(
    "user_value",
    [
        "cmk admin",
        "cmkadmin    ",
        "\tcmkadmin",
        "foo/../",
        "%2F",
        ".",
        "@example.com",
    ],
)
def test_invalid_user(user_value: str) -> None:
    with pytest.raises(ValueError, match="invalid username"):
        UserId(user_value)


def test_invalid_user_too_long() -> None:
    too_long_val = 64 * "𐌈"
    with pytest.raises(ValueError, match="too long"):
        UserId(too_long_val)

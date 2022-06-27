#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.wato.special_agents.innovaphone import special_agents_innovaphone_transform


@pytest.mark.parametrize(
    "parameters, expected_result",
    [
        (
            ("USER123", "PasswordABC"),
            {
                "auth_basic": {"password": ("password", "PasswordABC"), "username": "USER123"},
            },
        ),
    ],
)
def test__special_agents_innovaphone_transform(parameters, expected_result) -> None:
    assert special_agents_innovaphone_transform(parameters) == expected_result

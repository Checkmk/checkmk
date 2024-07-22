#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.lib.prometheus import extract_connection_args, LoginAuth, TokenAuth


@pytest.mark.parametrize(
    ["config", "authentication", "expected_result"],
    [
        pytest.param(
            {
                "connection": "1.2.3.4",
                "protocol": "http",
            },
            None,
            {
                "api_url": "http://1.2.3.4/api/v1/",
                "verify-cert": False,
            },
            id="no authentication",
        ),
        pytest.param(
            {
                "connection": "1.2.3.4",
                "protocol": "http",
            },
            LoginAuth(
                username="user",
                password="secret",
            ),
            {
                "api_url": "http://1.2.3.4/api/v1/",
                "auth": ("user", "secret"),
                "verify-cert": False,
            },
            id="authentication with login",
        ),
        pytest.param(
            {
                "connection": "my-host.com",
                "verify_cert": True,
                "protocol": "https",
            },
            TokenAuth("token"),
            {
                "api_url": "https://my-host.com/api/v1/",
                "token": "token",
                "verify-cert": True,
            },
            id="authentication with token",
        ),
    ],
)
def test_extract_connection_args(
    config: Mapping[str, object],
    authentication: LoginAuth | TokenAuth | None,
    expected_result: Mapping[str, object],
) -> None:
    assert extract_connection_args(config, authentication) == expected_result

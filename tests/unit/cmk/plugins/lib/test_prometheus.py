#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest
from pytest_mock import MockerFixture

from cmk.plugins.lib.prometheus import extract_connection_args


@pytest.mark.parametrize(
    ["config", "expected_result"],
    [
        pytest.param(
            {
                "connection": "1.2.3.4",
                "auth_basic": (
                    "auth_login",
                    {
                        "username": "user",
                        "password": (
                            "password",
                            "secret",
                        ),
                    },
                ),
                "protocol": "http",
            },
            {
                "api_url": "http://1.2.3.4/api/v1/",
                "auth": ("user", "secret"),
                "verify-cert": False,
            },
            id="explicit_login",
        ),
        pytest.param(
            {
                "connection": "my-host.com",
                "auth_basic": (
                    "auth_login",
                    {
                        "username": "user",
                        "password": (
                            "store",
                            "prometheus",
                        ),
                    },
                ),
                "protocol": "https",
            },
            {
                "auth": ("user", "very_secret"),
                "api_url": "https://my-host.com/api/v1/",
                "verify-cert": False,
            },
            id="pwstore_login",
        ),
        pytest.param(
            {
                "connection": "my-host.com",
                "auth_basic": (
                    "auth_token",
                    {
                        "token": (
                            "password",
                            "token",
                        ),
                    },
                ),
                "verify-cert": True,
                "protocol": "https",
            },
            {
                "api_url": "https://my-host.com/api/v1/",
                "token": "token",
                "verify-cert": True,
            },
            id="explicit_token",
        ),
        pytest.param(
            {
                "connection": "later1.2.3.4:9876/somewhere.",
                "auth_basic": (
                    "auth_token",
                    {
                        "token": (
                            "store",
                            "prometheus",
                        ),
                    },
                ),
                "verify-cert": True,
                "protocol": "https",
            },
            {
                "api_url": "https://later1.2.3.4:9876/somewhere./api/v1/",
                "token": "very_secret",
                "verify-cert": True,
            },
            id="pwstore_token",
        ),
    ],
)
def test_extract_connection_args(
    mocker: MockerFixture,
    config: Mapping[str, object],
    expected_result: Mapping[str, object],
) -> None:
    mocker.patch(
        "cmk.utils.password_store._pwstore.load",
        return_value={
            "prometheus": "very_secret",
            "something_else": "123",
        },
    )
    assert extract_connection_args(config) == expected_result

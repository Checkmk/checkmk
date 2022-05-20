#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

import pytest
from pytest_mock import MockerFixture

from cmk.special_agents.utils.prometheus import extract_connection_args


@pytest.mark.parametrize(
    ["config", "expected_result"],
    [
        pytest.param(
            {
                "connection": (
                    "ip_address",
                    {},
                ),
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
                "host_address": "1.2.3.4",
                "host_name": "prometheus",
            },
            {
                "address": "1.2.3.4",
                "auth": ("user", "secret"),
                "port": None,
                "protocol": "http",
                "verify-cert": False,
            },
            id="explicit_login",
        ),
        pytest.param(
            {
                "connection": (
                    "url_custom",
                    {"url_address": "my-host.com"},
                ),
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
                "host_address": "1.2.3.4",
                "host_name": "prometheus",
            },
            {
                "auth": ("user", "very_secret"),
                "protocol": "https",
                "url_custom": "my-host.com",
                "verify-cert": False,
            },
            id="pwstore_login",
        ),
        pytest.param(
            {
                "connection": (
                    "url_custom",
                    {"url_address": "my-host.com"},
                ),
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
                "host_address": "1.2.3.4",
                "host_name": "prometheus",
            },
            {
                "protocol": "https",
                "token": "token",
                "url_custom": "my-host.com",
                "verify-cert": True,
            },
            id="explicit_token",
        ),
        pytest.param(
            {
                "connection": (
                    "ip_address",
                    {
                        "port": 9876,
                        "path-prefix": "somewhere.",
                    },
                ),
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
                "host_address": "1.2.3.4",
                "host_name": "prometheus",
            },
            {
                "address": "somewhere.1.2.3.4",
                "port": 9876,
                "protocol": "https",
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
        "cmk.utils.password_store.load",
        return_value={
            "prometheus": "very_secret",
            "something_else": "123",
        },
    )
    assert extract_connection_args(config) == expected_result

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

import pytest
from pytest_mock import MockerFixture

from cmk.special_agents.agent_prometheus import _extract_connection_args


@pytest.mark.parametrize(
    ["config", "expected_result"],
    [
        pytest.param(
            {
                "connection": "ip_address",
                "auth_basic": {
                    "username": "user",
                    "password": (
                        "password",
                        "secret",
                    ),
                },
                "protocol": "http",
                "host_address": "1.2.3.4",
                "host_name": "prometheus",
            },
            {
                "address": "1.2.3.4",
                "auth": ("user", "secret"),
                "port": "",
                "protocol": "http",
            },
            id="explicit_login",
        ),
        pytest.param(
            {
                "connection": (
                    "url_custom",
                    {
                        "url_address": "my-host.com"
                    },
                ),
                "auth_basic": {
                    "username": "user",
                    "password": (
                        "store",
                        "prometheus",
                    ),
                },
                "protocol": "https",
                "host_address": "1.2.3.4",
                "host_name": "prometheus",
            },
            {
                "auth": ("user", "very_secret"),
                "port": "",
                "protocol": "https",
                "url_custom": "my-host.com",
            },
            id="pwstore_login",
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
    assert _extract_connection_args(config) == expected_result

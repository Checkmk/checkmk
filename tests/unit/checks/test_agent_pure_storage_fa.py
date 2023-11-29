#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from tests.testlib import SpecialAgent

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params, host_ip_address, hostname, expected_args",
    [
        pytest.param(
            {
                "timeout": 1,
                "ssl": True,
                "api_token": ("store", "stored_secret"),
            },
            "1.2.3.4",
            "host",
            [
                "--timeout",
                "1",
                "--cert-server-name",
                "host",
                "--api-token",
                ("store", "stored_secret", "%s"),
                "1.2.3.4",
            ],
            id="Available timeout and ssl True and stored api token",
        ),
        pytest.param(
            {
                "ssl": False,
                "api_token": "api_token",
            },
            None,
            "host",
            [
                "--no-cert-check",
                "--api-token",
                "api_token",
                "host",
            ],
            id="No timeout and ssl False",
        ),
        pytest.param(
            {
                "ssl": "something_else",
                "api_token": "api_token",
            },
            "1.2.3.4",
            "host",
            [
                "--cert-server-name",
                "something_else",
                "--api-token",
                "api_token",
                "1.2.3.4",
            ],
            id="No timeout and ssl custom",
        ),
    ],
)
def test_pure_storage_fa_argument_parsing(
    params: dict,
    expected_args: list[str | tuple[str, str, str]],
    host_ip_address: str | None,
    hostname: str,
) -> None:
    agent = SpecialAgent("agent_pure_storage_fa")
    arguments = agent.argument_func(params, hostname, host_ip_address)
    assert arguments == expected_args

#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence

import pytest

from tests.testlib import SpecialAgent


@pytest.mark.parametrize(
    ["params", "expected_args"],
    [
        pytest.param(
            {
                "username": "mobileironuser",
                "password": ("password", "mobileironpassword"),
                "proxy_details": {
                    "proxy_host": "localhost",
                    "proxy_port": 8080,
                    "proxy_user": "mobileironproxyuser",
                    "proxy_password": ("password", "mobileironproxypassword"),
                },
                "port": 443,
                "no-cert-check": True,
                "partition": ["10"],
            },
            [
                "-u",
                "mobileironuser",
                "-p",
                "mobileironpassword",
                "--port",
                443,
                "--no-cert-check",
                "--partition",
                "10",
                "--hostname",
                "mobileironhostname",
                "--proxy-host",
                "localhost",
                "--proxy-port",
                "8080",
                "--proxy-user",
                "mobileironproxyuser",
                "--proxy-password",
                "mobileironproxypassword",
            ],
            id="explicit_password",
        ),
        pytest.param(
            {
                "username": "mobileironuser",
                "password": ("store", "mobileironpassword"),
            },
            [
                "-u",
                "mobileironuser",
                "-p",
                ("store", "mobileironpassword", "%s"),
                "--hostname",
                "mobileironhostname",
            ],
            id="password_from_store",
        ),
    ],
)
def test_agent_mobileiron_arguments(
    params: Mapping[str, Any],
    expected_args: Sequence[Any],
) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_mobileiron")
    arguments = agent.argument_func(params, "mobileironhostname", "address")
    assert arguments == expected_args

#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import SpecialAgent

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params, expected_args",
    [
        (
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
                "hostname": "mobileironhostname",
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
        ),
    ],
)
def test_mobileiron_argument_parsing(params, expected_args):
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_mobileiron")
    arguments = agent.argument_func(params, "mobileironhostname", "address")
    assert arguments == expected_args

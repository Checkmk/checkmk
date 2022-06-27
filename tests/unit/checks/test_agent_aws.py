#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
                "access_key_id": "strawberry",
                "secret_access_key": ("password", "strawberry098"),
                "proxy_details": {
                    "proxy_host": "1.1.1",
                    "proxy_port": 22,
                    "proxy_user": "banana",
                    "proxy_password": ("password", "banana123"),
                },
                "assume_role": {},
                "global_services": {
                    "ce": None,
                },
                "regions": [],
                "services": {
                    "ec2": {
                        "selection": "all",
                        "limits": True,
                    },
                    "ebs": {
                        "selection": "all",
                        "limits": True,
                    },
                    "cloudfront": None,
                },
            },
            [
                "--access-key-id",
                "strawberry",
                "--secret-access-key",
                "strawberry098",
                "--proxy-host",
                "1.1.1",
                "--proxy-port",
                "22",
                "--proxy-user",
                "banana",
                "--proxy-password",
                "banana123",
                "--global-services",
                "ce",
                "--services",
                "cloudfront",
                "ebs",
                "ec2",
                "--ec2-limits",
                "--ebs-limits",
                "--hostname",
                "testhost",
            ],
            id="explicit_passwords",
        ),
        pytest.param(
            {
                "access_key_id": "strawberry",
                "secret_access_key": ("store", "strawberry098"),
                "proxy_details": {
                    "proxy_host": "1.1.1",
                    "proxy_user": "banana",
                    "proxy_password": ("store", "banana123"),
                },
                "assume_role": {},
                "global_services": {},
                "regions": [],
                "services": {},
            },
            [
                "--access-key-id",
                "strawberry",
                "--secret-access-key",
                ("store", "strawberry098", "%s"),
                "--proxy-host",
                "1.1.1",
                "--proxy-user",
                "banana",
                "--proxy-password",
                ("store", "banana123", "%s"),
                "--hostname",
                "testhost",
            ],
            id="passwords_from_store",
        ),
    ],
)
def test_aws_argument_parsing(
    params: Mapping[str, Any],
    expected_args: Sequence[Any],
) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_aws")
    arguments = agent.argument_func(params, "testhost", "address")
    assert arguments == expected_args

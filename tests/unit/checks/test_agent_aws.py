#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from tests.testlib import SpecialAgent

from cmk.base.sources.programs import SpecialAgentConfiguration

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params, expected_args",
    [
        (
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
            SpecialAgentConfiguration(
                [
                    "--proxy-host",
                    "1.1.1",
                    "--proxy-port",
                    "22",
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
                json.dumps(
                    {
                        "access_key_id": "strawberry",
                        "secret_access_key": "strawberry098",
                        "proxy_user": "banana",
                        "proxy_password": "banana123",
                    }
                ),
            ),
        ),
    ],
)
def test_aws_argument_parsing(params, expected_args):
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_aws")
    arguments = agent.argument_func(params, "testhost", "address")
    assert arguments == expected_args

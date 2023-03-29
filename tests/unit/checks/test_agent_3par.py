#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from tests.testlib import SpecialAgent

from cmk.base.config import SpecialAgentInfoFunctionResult


@pytest.mark.parametrize(
    "params,result",
    [
        (
            {
                "user": "user",
                "password": "d1ng",
                "port": 8080,
                "verify_cert": False,
                "values": ["x", "y"],
            },
            [
                "--user",
                "user",
                "--password",
                "d1ng",
                "--port",
                8080,
                "--no-cert-check",
                "--values",
                "x,y",
                "address",
            ],
        ),
        (
            {
                "user": "user",
                "password": "d1ng",
                "port": 1234,
                "values": ["x", "y"],
            },
            [
                "--user",
                "user",
                "--password",
                "d1ng",
                "--port",
                1234,
                "--no-cert-check",
                "--values",
                "x,y",
                "address",
            ],
        ),
        (
            {
                "user": "user",
                "password": "d1ng",
                "port": 8090,
                "verify_cert": True,
                "values": ["x", "y"],
            },
            ["--user", "user", "--password", "d1ng", "--port", 8090, "--values", "x,y", "address"],
        ),
        (
            {
                "user": "user",
                "password": "d1ng",
                "port": 500,
                "verify_cert": True,
            },
            ["--user", "user", "--password", "d1ng", "--port", 500, "address"],
        ),
        (
            {
                "user": "user",
                "password": ("store", "pw-id"),
                "port": 8079,
                "verify_cert": True,
            },
            ["--user", "user", "--password", ("store", "pw-id", "%s"), "--port", 8079, "address"],
        ),
    ],
)
def test_3par(params: Mapping[str, object], result: SpecialAgentInfoFunctionResult) -> None:
    agent = SpecialAgent("agent_3par")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == result

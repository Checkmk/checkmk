#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence

import pytest

from tests.testlib import SpecialAgent


@pytest.mark.parametrize(
    ["params", "expected_result"],
    [
        pytest.param(
            {
                "username": "user",
                "password": ("password", "passwd"),
                "port": "443",
                "no-cert-check": True,
                "timeout": "30",
                "log-cutoff-weeks": "4",
            },
            [
                "-u",
                "user",
                "-p",
                "passwd",
                "--port",
                "443",
                "--no-cert-check",
                "--timeout",
                "30",
                "--log-cutoff-weeks",
                "4",
                "testhost",
            ],
            id="explicit_password",
        ),
        pytest.param(
            {
                "username": "user",
                "password": ("store", "passwd"),
                "timeout": "40",
            },
            [
                "-u",
                "user",
                "-p",
                ("store", "passwd", "%s"),
                "--timeout",
                "40",
                "testhost",
            ],
            id="password_from_store",
        ),
    ],
)
def test_agent_proxmox_ve_arguments(
    params: Mapping[str, Any],
    expected_result: Sequence[Any],
) -> None:
    assert (
        SpecialAgent("agent_proxmox_ve").argument_func(
            params,
            "testhost",
            "1.2.3.4",
        )
        == expected_result
    )

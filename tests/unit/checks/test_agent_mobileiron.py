#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.testlib import SpecialAgent


@pytest.mark.parametrize(
    ["params", "expected_args"],
    [
        pytest.param(
            {
                "username": "mobileironuser",
                "password": ("password", "mobileironpassword"),
                "proxy": (
                    "url",
                    "abc:8567",
                ),
                "partition": ["10"],
                "key-fields": ("somefield",),
                "android-regex": ["asdf", "foo", "^bar"],
                "ios-regex": [".*"],
                "other-regex": [".*"],
            },
            [
                "-u",
                "mobileironuser",
                "-p",
                "mobileironpassword",
                "--partition",
                "10",
                "--hostname",
                "mobileironhostname",
                "--proxy",
                "abc:8567",
                "--android-regex=asdf",
                "--android-regex=foo",
                "--android-regex=^bar",
                "--ios-regex=.*",
                "--other-regex=.*",
                "--key-fields",
                "somefield",
            ],
            id="explicit_password",
        ),
        pytest.param(
            {
                "username": "mobileironuser",
                "password": ("store", "mobileironpassword"),
                "key-fields": ("somefield",),
            },
            [
                "-u",
                "mobileironuser",
                "-p",
                ("store", "mobileironpassword", "%s"),
                "--hostname",
                "mobileironhostname",
                "--key-fields",
                "somefield",
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

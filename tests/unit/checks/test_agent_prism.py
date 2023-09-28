#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.testlib import SpecialAgent

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    ["params", "expected_args"],
    [
        pytest.param(
            {"username": "", "password": ("password", "")},
            ["--server", "address", "--username", "", "--password", ""],
            id="explicit password and no port",
        ),
        pytest.param(
            {"username": "userid", "password": ("password", "password"), "port": 9440},
            [
                "--server",
                "address",
                "--username",
                "userid",
                "--password",
                "password",
                "--port",
                "9440",
            ],
            id="explicit password and port",
        ),
        pytest.param(
            {"username": "userid", "password": ("store", "prism"), "port": 9440},
            [
                "--server",
                "address",
                "--username",
                "userid",
                "--password",
                ("store", "prism", "%s"),
                "--port",
                "9440",
            ],
            id="password from store and port",
        ),
    ],
)
def test_prism_argument_parsing(params: Mapping[str, Any], expected_args: Sequence[Any]) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_prism")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args

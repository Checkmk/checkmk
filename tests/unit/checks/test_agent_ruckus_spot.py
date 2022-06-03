#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence

import pytest

from tests.testlib import SpecialAgent

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    ["params", "expected_args"],
    [
        pytest.param(
            {
                "venueid": "venueID",
                "api_key": ("password", "55410aaa"),
                "port": 8443,
                "address": True,
            },
            ["--address", "address", "8443", "--venueid", "venueID", "--apikey", "55410aaa"],
            id="with explicit password",
        ),
        pytest.param(
            {
                "venueid": "venueID",
                "api_key": ("store", "ruckus_spot"),
                "port": 8443,
                "address": True,
            },
            [
                "--address",
                "address",
                "8443",
                "--venueid",
                "venueID",
                "--apikey",
                ("store", "ruckus_spot", "%s"),
            ],
            id="with password from store",
        ),
        pytest.param(
            {
                "cmk_agent": {"port": 6556},
                "venueid": "venueID",
                "api_key": ("password", "55410aaa"),
                "port": 8443,
                "address": "addresstest",
            },
            [
                "--address",
                "addresstest",
                "8443",
                "--venueid",
                "venueID",
                "--apikey",
                "55410aaa",
                "--agent_port",
                "6556",
            ],
            id="with explicit password and cmk_agent argument",
        ),
    ],
)
def test_ruckus_spot_argument_parsing(
    params: Mapping[str, Any], expected_args: Sequence[Any]
) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_ruckus_spot")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args

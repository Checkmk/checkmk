#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import SpecialAgent

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            {"venueid": "venueID", "api_key": "55410aaa", "port": 8443, "address": True},
            ["--address", "address", "8443", "--venueid", "venueID", "--apikey", "55410aaa"],
        ),
        (
            {
                "cmk_agent": {"port": 6556},
                "venueid": "venueID",
                "api_key": "55410aaa",
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
        ),
    ],
)
def test_ruckus_spot_argument_parsing(params, expected_args):
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_ruckus_spot")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args

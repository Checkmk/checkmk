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
        ({}, ["--host", "address"]),
        (
            {"segment_display_brightness": 5, "segment_display_uid": "8888", "port": 4223},
            [
                "--host",
                "address",
                "--port",
                "4223",
                "--segment_display_uid",
                "8888",
                "--segment_display_brightness",
                "5",
            ],
        ),
    ],
)
def test_tinkerforge_argument_parsing(params, expected_args) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_tinkerforge")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args

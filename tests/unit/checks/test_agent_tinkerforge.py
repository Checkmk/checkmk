#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from .checktestlib import SpecialAgent

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
def test_tinkerforge_argument_parsing(
    params: Mapping[str, object], expected_args: list[str]
) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_tinkerforge")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args

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
            {"username": "user", "password": ("password", "password"), "skip_elements": []},
            [
                "address",
                "user",
                "password",
                "--no_counters",
            ],
            id="no elements to skip",
        ),
        pytest.param(
            {
                "username": "user",
                "password": ("password", "password"),
                "skip_elements": ["ctr_volumes"],
            },
            [
                "address",
                "user",
                "password",
                "--no_counters",
                "volumes",
            ],
            id="skip volumes and explicit password",
        ),
        pytest.param(
            {"username": "user", "password": ("store", "netapp"), "skip_elements": ["ctr_volumes"]},
            [
                "address",
                "user",
                ("store", "netapp", "%s"),
                "--no_counters",
                "volumes",
            ],
            id="skip volumes and password from store",
        ),
    ],
)
def test_netapp_argument_parsing(params: Mapping[str, Any], expected_args: Sequence[Any]) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_netapp")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args

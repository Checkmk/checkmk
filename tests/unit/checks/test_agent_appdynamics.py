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
            {"username": "testID", "application": "appName", "password": ("store", "appdynamics")},
            ["-u", "testID", "-p", ("store", "appdynamics", "%s"), "address", "appName"],
            id="passwords_from_store",
        ),
        pytest.param(
            {
                "username": "testID",
                "application": "appName",
                "password": ("password", "password"),
                "port": 8090,
                "timeout": 30,
            },
            ["-u", "testID", "-p", "password", "-P", "8090", "-t", "30", "address", "appName"],
            id="explicit_passwords",
        ),
    ],
)
def test_appdynamics_argument_parsing(
    params: Mapping[str, Any], expected_args: Sequence[Any]
) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_appdynamics")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args

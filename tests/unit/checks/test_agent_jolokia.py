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
        pytest.param({}, ["--server", "address"], id="without parameters"),
        pytest.param(
            {"port": 8080},
            ["--server", "address", "--port", "8080"],
            id="with port value",
        ),
        pytest.param(
            {"instance": "monitor", "port": 8080},
            ["--server", "address", "--port", "8080", "--instance", "monitor"],
            id="with instance and port values",
        ),
        pytest.param(
            {"login": ("userID", ("password", "password"), "basic"), "port": 8080},
            [
                "--server",
                "address",
                "--port",
                "8080",
                "--user",
                "userID",
                "--password",
                "password",
                "--mode",
                "basic",
            ],
            id="explicit password",
        ),
        pytest.param(
            {"login": ("userID", ("store", "jolokia"), "basic"), "port": 8080},
            [
                "--server",
                "address",
                "--port",
                "8080",
                "--user",
                "userID",
                "--password",
                ("store", "jolokia", "%s"),
                "--mode",
                "basic",
            ],
            id="password from the store",
        ),
    ],
)
def test_jolokia_argument_parsing(params: Mapping[str, Any], expected_args: Sequence[Any]) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_jolokia")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args

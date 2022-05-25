#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence

import pytest

from tests.testlib import SpecialAgent


@pytest.mark.parametrize(
    ["params", "result"],
    [
        pytest.param(
            {"username": "user", "password": ("password", "test")},
            ["address", "8008", "user", "test"],
            id="explicit_password_and_default_port",
        ),
        pytest.param(
            {"username": "user", "password": ("store", "ddn_s2a")},
            ["address", "8008", "user", ("store", "ddn_s2a", "%s")],
            id="password_from_store_and_default_port",
        ),
        pytest.param(
            {"username": "user", "password": ("password", "test"), "port": 8090},
            ["address", "8090", "user", "test"],
            id="explicit_password_and_port_8090",
        ),
    ],
)
def test_ddn_s2a(params: Mapping[str, Any], result: Sequence[Any]) -> None:
    agent = SpecialAgent("agent_ddn_s2a")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == result

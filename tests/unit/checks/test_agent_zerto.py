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
            {"username": "usr", "password": ("password", "passwd")},
            ["--authentication", "windows", "-u", "usr", "-p", "passwd", "address"],
            id="with explicit password",
        ),
        pytest.param(
            {"username": "usr", "password": ("store", "zerto")},
            ["--authentication", "windows", "-u", "usr", "-p", ("store", "zerto", "%s"), "address"],
            id="with password from store",
        ),
    ],
)
def test_zerto_argument_parsing(params: Mapping[str, Any], expected_args: Sequence[Any]) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_zerto")
    arguments = agent.argument_func(params, "testhost", "address")
    assert arguments == expected_args

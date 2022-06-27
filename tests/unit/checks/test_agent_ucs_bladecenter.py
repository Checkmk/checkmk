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
    "params,expected_args",
    [
        pytest.param(
            {"username": "username", "password": ("password", "password")},
            ["-u", "username", "-p", "password", "address"],
            id="with explicit password",
        ),
        pytest.param(
            {"username": "username", "password": ("store", "ucs_bladecenter")},
            ["-u", "username", "-p", ("store", "ucs_bladecenter", "%s"), "address"],
            id="with password from store",
        ),
    ],
)
def test_ucs_bladecenter_argument_parsing(
    params: Mapping[str, Any], expected_args: Sequence[Any]
) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_ucs_bladecenter")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args

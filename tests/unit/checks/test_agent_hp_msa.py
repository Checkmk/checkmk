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
                "username": "user",
                "password": ("password", "password"),
            },
            ["-u", "user", "-p", "password", "address"],
            id="explicit_passwords",
        ),
        pytest.param(
            {
                "username": "user",
                "password": ("store", "hp_msa"),
            },
            ["-u", "user", "-p", ("store", "hp_msa", "%s"), "address"],
            id="passwords_from_store",
        ),
    ],
)
def test_hp_msa_argument_parsing(params: Mapping[str, Any], expected_args: Sequence[Any]) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_hp_msa")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args

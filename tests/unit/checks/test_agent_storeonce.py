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
            {"password": ("password", "password"), "user": "username"},
            ["--address=host", "--user=username", "--password=password"],
            id="with explicit password",
        ),
        pytest.param(
            {"password": ("store", "storeonce"), "user": "username"},
            ["--address=host", "--user=username", "--password=('store', 'storeonce', '%s')"],
            id="with password from store",
        ),
        pytest.param(
            {"cert": True, "password": ("password", "password"), "user": "username"},
            ["--address=host", "--user=username", "--password=password"],
            id="with explicit password and cert=True",
        ),
        pytest.param(
            {"cert": False, "password": ("password", "password"), "user": "username"},
            ["--address=host", "--user=username", "--password=password", "--no-cert-check"],
            id="with explicit password and cert=False",
        ),
    ],
)
def test_storeonce_argument_parsing(
    params: Mapping[str, Any], expected_args: Sequence[Any]
) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_storeonce")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence

import pytest

from tests.testlib import SpecialAgent


@pytest.mark.parametrize(
    "params, expected_args",
    [
        (
            {
                "subscription": "banana",
                "tenant": "strawberry",
                "client": "blueberry",
                "secret": "vurystrong",
                "config": {},
            },
            [
                "--subscription",
                "banana",
                "--tenant",
                "strawberry",
                "--client",
                "blueberry",
                "--secret",
                "vurystrong",
            ],
        ),
    ],
)
def test_azure_argument_parsing(
    params: Mapping[str, Any],
    expected_args: Sequence[Any],
) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_azure")
    arguments = agent.argument_func(params, "testhost", "address")
    assert arguments == expected_args

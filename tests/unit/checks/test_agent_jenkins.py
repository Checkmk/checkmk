#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from tests.testlib import SpecialAgent


@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {
                "user": "username",
                "password": ("password", "passwd"),
                "instance": "test",
                "protocol": "https",
            },
            [
                "-P",
                "https",
                "-u",
                "username",
                "-s",
                "passwd",
                "test",
            ],
            id="only required params",
        ),
        pytest.param(
            {
                "user": "username",
                "password": ("password", "passwd"),
                "instance": "test",
                "protocol": "https",
                "port": 442,
                "sections": ["instance", "jobs", "nodes", "queue"],
            },
            [
                "-P",
                "https",
                "-u",
                "username",
                "-s",
                "passwd",
                "-m",
                "instance jobs nodes queue",
                "-p",
                442,
                "test",
            ],
            id="all params",
        ),
    ],
)
def test_agent_jenkins_arguments_password_store(
    params: Mapping[str, object], expected_result: Sequence[str]
) -> None:
    agent = SpecialAgent("agent_jenkins")
    assert agent.argument_func(params, "testhost", "1.2.3.4") == expected_result

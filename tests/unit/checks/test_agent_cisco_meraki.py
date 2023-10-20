#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.testlib import SpecialAgent


@pytest.mark.parametrize(
    "params, expected_args",
    [
        pytest.param(
            {
                "api_key": ("password", "my-api-key"),
            },
            [
                "testhost",
                "my-api-key",
            ],
            id="Default arguments",
        ),
        pytest.param(
            {
                "api_key": ("password", "my-api-key"),
                "proxy": (
                    "url",
                    "abc:8567",
                ),
            },
            [
                "testhost",
                "my-api-key",
                "--proxy",
                "abc:8567",
            ],
            id="Proxy settings, url proxy",
        ),
        pytest.param(
            {
                "api_key": ("password", "my-api-key"),
                "proxy": (
                    "environment",
                    "environment",
                ),
            },
            [
                "testhost",
                "my-api-key",
                "--proxy",
                "FROM_ENVIRONMENT",
            ],
            id="Proxy settings, environment proxy",
        ),
        pytest.param(
            {
                "api_key": ("password", "my-api-key"),
                "proxy": (
                    "no_proxy",
                    None,
                ),
            },
            [
                "testhost",
                "my-api-key",
                "--proxy",
                "NO_PROXY",
            ],
            id="Proxy settings, no proxy",
        ),
        pytest.param(
            {
                "api_key": ("password", "my-api-key"),
                "proxy": (
                    "global",
                    "test_proxy",
                ),
            },
            [
                "testhost",
                "my-api-key",
                "--proxy",
                "FROM_ENVIRONMENT",
            ],
            id="Proxy settings, global proxy not found in gloabl config",
        ),
        pytest.param(
            {
                "api_key": ("password", "my-api-key"),
                "sections": ["sec1", "sec2"],
            },
            [
                "testhost",
                "my-api-key",
                "--sections",
                "sec1",
                "sec2",
            ],
            id="Sections",
        ),
        pytest.param(
            {
                "api_key": ("password", "my-api-key"),
                "orgs": ["org1", "org2"],
            },
            [
                "testhost",
                "my-api-key",
                "--orgs",
                "org1",
                "org2",
            ],
            id="Organisation IDs",
        ),
    ],
)
def test_aws_argument_parsing(
    params: Mapping[str, Any],
    expected_args: Sequence[str],
) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_cisco_meraki")
    assert expected_args == agent.argument_func(params, "testhost", "address")

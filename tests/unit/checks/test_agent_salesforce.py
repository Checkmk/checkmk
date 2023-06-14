#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from tests.testlib import SpecialAgent

from cmk.base.config import SpecialAgentInfoFunctionResult

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params,expected_args",
    [
        pytest.param(
            {"instances": ["5"]},
            [
                "--section_url",
                "salesforce_instances,https://api.status.salesforce.com/v1/instances/5/status",
            ],
            id="single instance",
        ),
        pytest.param(
            {"instances": ["foo", "bar"]},
            [
                "--section_url",
                "salesforce_instances,https://api.status.salesforce.com/v1/instances/foo/status",
                "--section_url",
                "salesforce_instances,https://api.status.salesforce.com/v1/instances/bar/status",
            ],
            id="multiple instances",
        ),
    ],
)
def test_agent_salesforce_argument_parsing(
    params: Mapping[str, object], expected_args: SpecialAgentInfoFunctionResult
) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_salesforce")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args

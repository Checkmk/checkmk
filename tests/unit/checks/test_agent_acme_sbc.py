#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.base.server_side_calls import SpecialAgentInfoFunctionResult

from .checktestlib import SpecialAgent

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (None, ["host"]),
    ],
)
def test_acme_sbc_argument_parsing(
    params: Mapping[str, object], expected_args: SpecialAgentInfoFunctionResult
) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_acme_sbc")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args

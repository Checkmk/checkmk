#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc import version

from cmk.special_agents import agent_jolokia, agent_vsphere


@pytest.mark.parametrize(
    "user_agent",
    [
        agent_jolokia.USER_AGENT,
        agent_vsphere.USER_AGENT,
    ],
)
def test_user_agent_string(user_agent: str) -> None:
    assert user_agent.startswith("checkmk-special-")
    assert user_agent.endswith(f"-{version.__version__}")

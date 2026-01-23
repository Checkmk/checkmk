#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: RUF100
# ruff: noqa: I001

import pytest
from agents.plugins import apache_status, mk_jolokia, nginx_status

from cmk.ccc import version


@pytest.mark.parametrize(
    "user_agent",
    [
        apache_status.USER_AGENT,
        mk_jolokia.USER_AGENT,
        nginx_status.USER_AGENT,
    ],
)
def test_user_agent_string(user_agent: str) -> None:
    assert user_agent.startswith("checkmk-agent-")
    assert user_agent.endswith(f"-{version.__version__}")

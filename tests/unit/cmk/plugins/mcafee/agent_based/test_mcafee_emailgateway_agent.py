#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.mcafee.agent_based.mcafee_emailgateway_agent import (
    check_mcafee_emailgateway_agent,
    discover_mcafee_emailgateway_agent,
)

_STRING_TABLE: StringTable = [["3.6.0", "gw.example.com", "2026-01-01 00:00"]]


def test_discover() -> None:
    assert list(discover_mcafee_emailgateway_agent(_STRING_TABLE)) == [Service()]


def test_check() -> None:
    assert list(check_mcafee_emailgateway_agent(_STRING_TABLE)) == [
        Result(
            state=State.OK,
            summary="Version: 3.6.0, Hostname: gw.example.com, Last file update: 2026-01-01 00:00",
        )
    ]

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import render, Result, Service, State, StringTable
from cmk.plugins.mcafee.agent_based.mcafee_emailgateway_smtp import (
    check_mcafee_emailgateway_smtp,
    discover_mcafee_emailgateway_smtp,
)

_STRING_TABLE: StringTable = [["42", "1048576", "3", "7"]]


def test_discover() -> None:
    assert list(discover_mcafee_emailgateway_smtp(_STRING_TABLE)) == [Service()]


def test_check() -> None:
    assert list(check_mcafee_emailgateway_smtp(_STRING_TABLE)) == [
        Result(
            state=State.OK,
            summary=(
                f"Total connections: 42 ({render.bytes(1048576)}), "
                "Kernel blocked: 3, Kernel active: 7"
            ),
        )
    ]

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.legacy_checks.mcafee_emailgateway_spam_mcafee import (
    check_mcafee_emailgateway_spam_mcafee,
    discover_mcafee_emailgateway_spam_mcafee,
)

_STRING_TABLE: StringTable = [["3.0.0", "20260101"]]


def test_discover() -> None:
    assert list(discover_mcafee_emailgateway_spam_mcafee(_STRING_TABLE)) == [Service()]


def test_check() -> None:
    assert list(check_mcafee_emailgateway_spam_mcafee(_STRING_TABLE)) == [
        Result(state=State.OK, summary="Engine version: 3.0.0, Rules version: 20260101")
    ]

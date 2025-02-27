#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.cisco_sma.agent_based.mail_transfer_memory import (
    _check_mail_transfer_memory,
    _discover_mail_transfer_memory,
    _parse_mail_transfer_memory,
    MailTransferMemoryStatus,
    Params,
)


def test_discover_mail_transfer_memory() -> None:
    assert list(
        _discover_mail_transfer_memory(
            MailTransferMemoryStatus.memory_available,
        )
    ) == [Service()]


@pytest.mark.parametrize(
    "memory_status, expected",
    [
        (
            MailTransferMemoryStatus.memory_available,
            Result(state=State.OK, summary="Memory available"),
        ),
        (
            MailTransferMemoryStatus.memory_shortage,
            Result(state=State.WARN, summary="Memory shortage"),
        ),
        (
            MailTransferMemoryStatus.memory_full,
            Result(state=State.CRIT, summary="Memory full"),
        ),
    ],
)
def test_check_mail_transfer_memory(
    memory_status: MailTransferMemoryStatus, expected: State
) -> None:
    params = Params(
        monitoring_status_memory_available=State.OK.value,
        monitoring_status_memory_shortage=State.WARN.value,
        monitoring_status_memory_full=State.CRIT.value,
    )
    assert list(
        _check_mail_transfer_memory(params=params, section=memory_status),
    ) == [
        expected,
    ]


def test_parse_dns_requests() -> None:
    assert _parse_mail_transfer_memory([["1"]]) == MailTransferMemoryStatus.memory_available
    assert _parse_mail_transfer_memory([["2"]]) == MailTransferMemoryStatus.memory_shortage
    assert _parse_mail_transfer_memory([["3"]]) == MailTransferMemoryStatus.memory_full
    assert _parse_mail_transfer_memory([[]]) is None

#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.cisco_sma.agent_based.mail_transfer_threads import (
    _check_mail_transfer_threads,
    _parse_mail_transfer_threads,
    Params,
)


def test_check_transfer_memory_with_no_levels() -> None:
    params = Params(
        levels_upper=("no_levels", None),
        levels_lower=("no_levels", None),
    )
    assert list(
        _check_mail_transfer_threads(params=params, section=12),
    ) == [
        Result(state=State.OK, summary="Total: 12"),
        Metric("cisco_sma_mail_transfer_threads", 12.0),
    ]


def test_check_transfer_memory_with_levels() -> None:
    params = Params(
        levels_upper=("fixed", (500.0, 1000.0)),
        levels_lower=("fixed", (300.0, 600.0)),
    )
    assert list(
        _check_mail_transfer_threads(params=params, section=700),
    ) == [
        Result(state=State.WARN, summary="Total: 700 (warn/crit at 500/1000)"),
        Metric("cisco_sma_mail_transfer_threads", 700.0, levels=(500.0, 1000.0)),
    ]


def test_parse_dns_requests() -> None:
    assert _parse_mail_transfer_threads([["1"]]) == 1.0
    assert _parse_mail_transfer_threads([[]]) is None

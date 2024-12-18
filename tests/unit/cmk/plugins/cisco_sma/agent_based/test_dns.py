#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.cisco_sma.agent_based.dns import (
    _check_dns_requests,
    _parse_dns_requests,
    DNSRequests,
    Params,
)


def test_check_dns_requests_with_no_levels() -> None:
    params = Params(
        pending_dns_levels=("no_levels", None),
        outstanding_dns_levels=("no_levels", None),
    )
    assert list(
        _check_dns_requests(
            params=params,
            section=DNSRequests(outstanding=10, pending=20),
        ),
    ) == [
        Result(state=State.OK, summary="Pending: 20"),
        Metric("pending_dns_requests", 20.0),
        Result(state=State.OK, summary="Outstanding: 10"),
        Metric("outstanding_dns_requests", 10.0),
    ]


def test_parse_dns_requests() -> None:
    assert _parse_dns_requests([["10", "20"]]) == DNSRequests(outstanding=10, pending=20)
    assert _parse_dns_requests([]) is None

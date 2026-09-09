#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import MutableMapping

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.f5_bigip.agent_based.f5_bigip_conns import (
    check_f5_bigip_conns,
    ConnectionStats,
    ConnsParams,
    discover_f5_bigip_conns,
    parse_f5_bigip_conns,
)

from ..conftest import value_store

_STRING_TABLE = [["4001", "1500", "700", "300", "9000"]]

# One minute earlier, so the counters above yield 10/s native, 5/s compat and 100/s requests.
_VALUE_STORE: MutableMapping[str, object] = {
    "native": (0.0, 100),
    "compat": (0.0, 0),
    "stathttpreqs": (0.0, 3000),
}


def test_parse_f5_bigip_conns() -> None:
    assert parse_f5_bigip_conns(_STRING_TABLE) == [
        ConnectionStats(
            connections=4001,
            ssl_connections=1500,
            native_connections=700,
            compat_connections=300,
            http_requests=9000,
        )
    ]


def test_parse_f5_bigip_conns_unset_oids() -> None:
    """SSL and HTTP counters are absent on devices where they are not configured."""
    assert parse_f5_bigip_conns([["4001", "", "", "", ""]]) == [
        ConnectionStats(
            connections=4001,
            ssl_connections=None,
            native_connections=None,
            compat_connections=None,
            http_requests=None,
        )
    ]


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param(_STRING_TABLE, [Service()], id="itemless service"),
        pytest.param([], [], id="empty section"),
    ],
)
def test_discover_f5_bigip_conns(string_table: list[list[str]], expected: list[Service]) -> None:
    assert list(discover_f5_bigip_conns(parse_f5_bigip_conns(string_table))) == expected


@time_machine.travel(60.0)
def test_check_f5_bigip_conns_fixed_levels() -> None:
    params = ConnsParams(
        conns=("fixed", (4000, 5000)),
        ssl_conns=("fixed", (25000, 30000)),
        http_req_rate=("fixed", (500, 1000)),
    )
    with value_store(_VALUE_STORE):
        assert list(check_f5_bigip_conns(params, parse_f5_bigip_conns(_STRING_TABLE))) == [
            Result(state=State.WARN, summary="Connections: 4001.00 (warn/crit at 4000.00/5000.00)"),
            Metric("connections", 4001.0, levels=(4000.0, 5000.0)),
            Result(state=State.OK, summary="SSL connections: 1500.00"),
            Metric("connections_ssl", 1500.0, levels=(25000.0, 30000.0)),
            Result(state=State.OK, summary="Connections/s: 15.00"),
            Metric("connections_rate", 15.0),
            Result(state=State.OK, summary="HTTP requests/s: 100.00"),
            Metric("requests_per_second", 100.0, levels=(500.0, 1000.0)),
        ]


@time_machine.travel(60.0)
def test_check_f5_bigip_conns_rate_lower_levels() -> None:
    """Upper and lower connection-rate levels are now independent parameters."""
    params = ConnsParams(
        connections_rate=("fixed", (100, 200)),
        connections_rate_lower=("fixed", (20, 10)),
    )
    with value_store(_VALUE_STORE):
        results = list(check_f5_bigip_conns(params, parse_f5_bigip_conns(_STRING_TABLE)))
    assert results[4:6] == [
        Result(state=State.WARN, summary="Connections/s: 15.00 (warn/crit below 20.00/10.00)"),
        Metric("connections_rate", 15.0, levels=(100.0, 200.0)),
    ]


@time_machine.travel(60.0)
def test_check_f5_bigip_conns_no_levels() -> None:
    with value_store(_VALUE_STORE):
        assert list(check_f5_bigip_conns(ConnsParams(), parse_f5_bigip_conns(_STRING_TABLE))) == [
            Result(state=State.OK, summary="Connections: 4001.00"),
            Metric("connections", 4001.0),
            Result(state=State.OK, summary="SSL connections: 1500.00"),
            Metric("connections_ssl", 1500.0),
            Result(state=State.OK, summary="Connections/s: 15.00"),
            Metric("connections_rate", 15.0),
            Result(state=State.OK, summary="HTTP requests/s: 100.00"),
            Metric("requests_per_second", 100.0),
        ]


@time_machine.travel(60.0)
def test_check_f5_bigip_conns_unconfigured_ssl() -> None:
    """A device without SSL reports 'not configured' rather than a level check."""
    section = parse_f5_bigip_conns([["4001", "", "700", "300", ""]])
    with value_store(_VALUE_STORE):
        assert list(check_f5_bigip_conns(ConnsParams(), section)) == [
            Result(state=State.OK, summary="Connections: 4001.00"),
            Metric("connections", 4001.0),
            Result(state=State.OK, summary="SSL connections: not configured"),
            Result(state=State.OK, summary="Connections/s: 15.00"),
            Metric("connections_rate", 15.0),
            Result(state=State.OK, summary="HTTP requests/s: not configured"),
        ]


@time_machine.travel(60.0)
def test_check_f5_bigip_conns_empty_section() -> None:
    """Nothing to sum: every gauge reports as not configured, the rate stays at zero."""
    with value_store():
        assert list(check_f5_bigip_conns(ConnsParams(), [])) == [
            Result(state=State.OK, summary="Connections: not configured"),
            Result(state=State.OK, summary="SSL connections: not configured"),
            Result(state=State.OK, summary="Connections/s: 0.00"),
            Metric("connections_rate", 0.0),
            Result(state=State.OK, summary="HTTP requests/s: not configured"),
        ]

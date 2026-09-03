#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.legacy_checks import mcafee_emailgateway_bridge as plugin

_NOW = datetime.datetime(2026, 1, 1, 0, 0, 0, tzinfo=datetime.UTC).timestamp()


def _warm_value_store() -> dict[str, tuple[float, float]]:
    # get_rate needs a prior sample per counter, else it raises on first call.
    return {
        "mcafee_emailgateway_bridge.tcp": (_NOW, 100.0),
        "mcafee_emailgateway_bridge.udp": (_NOW, 200.0),
        "mcafee_emailgateway_bridge.icmp": (_NOW, 300.0),
    }


def test_parse_empty() -> None:
    assert plugin.parse_mcafee_emailgateway_bridge([]) is None


def test_discover() -> None:
    assert list(plugin.discover_mcafee_emailgateway_bridge([["0", "0", "0", "0", "0"]])) == [
        Service()
    ]


def test_check_rates_with_levels(monkeypatch: pytest.MonkeyPatch) -> None:
    value_store = _warm_value_store()
    monkeypatch.setattr(plugin, "get_value_store", lambda: value_store)

    with time_machine.travel(_NOW + 60, tick=False):
        results = list(
            plugin.check_mcafee_emailgateway_bridge(
                {"tcp": (0.5, 2.0)}, [["0", "0", "160", "200", "300"]]
            )
        )

    assert results == [
        Result(state=State.OK, summary="Bridge: present"),
        Result(state=State.OK, summary="Status: UP"),
        Result(
            state=State.WARN,
            summary="TCP: 1.00 packets received/s (warn/crit at 0.5/2.0 packets/s)",
        ),
        Metric("tcp_packets_received", 1.0, levels=(0.5, 2.0)),
        Result(state=State.OK, summary="UDP: 0.00 packets received/s"),
        Metric("udp_packets_received", 0.0),
        Result(state=State.OK, summary="ICMP: 0.00 packets received/s"),
        Metric("icmp_packets_received", 0.0),
    ]


def test_check_not_present_and_down(monkeypatch: pytest.MonkeyPatch) -> None:
    value_store = _warm_value_store()
    monkeypatch.setattr(plugin, "get_value_store", lambda: value_store)

    with time_machine.travel(_NOW + 60, tick=False):
        results = list(
            plugin.check_mcafee_emailgateway_bridge({}, [["1", "1", "100", "200", "300"]])
        )

    assert results[:2] == [
        Result(state=State.CRIT, summary="Bridge: not present"),
        Result(state=State.CRIT, summary="Status: down"),
    ]

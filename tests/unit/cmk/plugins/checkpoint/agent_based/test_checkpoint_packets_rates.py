#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Iterator, Mapping
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.checkpoint.agent_based import checkpoint_packets
from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel

# Anchored in UTC so the rates do not depend on the timezone the tests run in.
_NOW = datetime.datetime(2019, 10, 28, 8, 52, 18, tzinfo=ZoneInfo("UTC"))
_T0 = _NOW.timestamp() - 60.0

_COUNTER_KEYS = ("accepted", "rejected", "dropped", "logged", "espencrypted", "espdecrypted")

PARAMS: Mapping[str, SimpleLevelsConfigModel[int]] = dict.fromkeys(
    _COUNTER_KEYS, ("fixed", (100000, 200000))
)

# 600 more packets over 60 seconds is 10/s; the logged counter only advances by 60, so 1/s.
_SECOND_POLL = [[["720", "780", "810", "64"]], [["600", "660"]]]


@pytest.fixture(name="warm_value_store")
def warm_value_store_fixture(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """get_rate needs a previous sample per counter. The check aborts at the first
    uninitialised counter, so all six have to be seeded to see its full output."""
    store: dict[str, object] = {
        "accepted": (_T0, 120),
        "rejected": (_T0, 180),
        "dropped": (_T0, 210),
        "logged": (_T0, 4),
        "espencrypted": (_T0, 0),
        "espdecrypted": (_T0, 60),
    }
    monkeypatch.setattr(checkpoint_packets, "get_value_store", lambda: store)
    yield


@time_machine.travel(_NOW, tick=False)
def test_check_reports_a_rate_per_counter(warm_value_store: None) -> None:
    parsed = checkpoint_packets.parse_checkpoint_packets(_SECOND_POLL)

    assert list(checkpoint_packets.check_checkpoint_packets(PARAMS, parsed)) == [
        Result(state=State.OK, summary="Accepted: 10.0 pkts/s"),
        Metric("accepted", 10.0, levels=(100000.0, 200000.0)),
        Result(state=State.OK, summary="Rejected: 10.0 pkts/s"),
        Metric("rejected", 10.0, levels=(100000.0, 200000.0)),
        Result(state=State.OK, summary="Dropped: 10.0 pkts/s"),
        Metric("dropped", 10.0, levels=(100000.0, 200000.0)),
        Result(state=State.OK, summary="Logged: 1.0 pkts/s"),
        Metric("logged", 1.0, levels=(100000.0, 200000.0)),
        Result(state=State.OK, summary="EspEncrypted: 10.0 pkts/s"),
        Metric("espencrypted", 10.0, levels=(100000.0, 200000.0)),
        Result(state=State.OK, summary="EspDecrypted: 10.0 pkts/s"),
        Metric("espdecrypted", 10.0, levels=(100000.0, 200000.0)),
    ]


@time_machine.travel(_NOW, tick=False)
def test_check_crosses_the_configured_levels(warm_value_store: None) -> None:
    parsed = checkpoint_packets.parse_checkpoint_packets(
        [[["9000120", "180", "210", "4"]], [["0", "60"]]]
    )

    results = list(checkpoint_packets.check_checkpoint_packets(PARAMS, parsed))

    assert results[0] == Result(
        state=State.WARN,
        summary="Accepted: 150000.0 pkts/s (warn/crit at 100000.0 pkts/s/200000.0 pkts/s)",
    )

#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pytest import MonkeyPatch

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.poseidon.agent_based import poseidon_temp

STRING_TABLE = [["Bezeichnung Sensor 1", "1", "16.8 C"]]


def _section() -> poseidon_temp.Section:
    section = poseidon_temp.parse_poseidon_temp(STRING_TABLE)
    assert section is not None
    return section


def test_discover_poseidon_temp() -> None:
    assert list(poseidon_temp.discover_poseidon_temp(_section())) == [
        Service(item="Bezeichnung Sensor 1")
    ]


def test_check_poseidon_temp(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(poseidon_temp, "get_value_store", dict)
    assert list(poseidon_temp.check_poseidon_temp("Bezeichnung Sensor 1", {}, _section())) == [
        Result(state=State.OK, summary="Sensor Bezeichnung Sensor 1, State normal"),
        Metric("temp", 16.8),
        Result(state=State.OK, summary="Temperature: 16.8 °C"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (no levels found)",
        ),
    ]

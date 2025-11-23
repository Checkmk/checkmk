#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

import cmk.plugins.collection.agent_based.primekey_temperature
from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based.primekey_temperature import check, discover, parse
from cmk.plugins.lib.temperature import TempParamDict


@pytest.fixture
def empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    store = dict[str, object]()
    monkeypatch.setattr(
        cmk.plugins.collection.agent_based.primekey_temperature, "get_value_store", lambda: store
    )


def test_parse() -> None:
    assert parse([["31"]]) == {"CPU": 31.0}


def test_discover() -> None:
    assert list(discover(section={"CPU": 31.0})) == [Service(item="CPU")]


@pytest.mark.usefixtures("empty_value_store")
def test_check() -> None:
    assert list(
        check(
            item="CPU",
            params=TempParamDict({"levels": (20.0, 50.0)}),
            section={"CPU": 31.0},
        )
    ) == [
        Metric("temp", 31.0, levels=(20.0, 50.0)),
        Result(state=State.WARN, summary="Temperature: 31.0 °C (warn/crit at 20.0 °C/50.0 °C)"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.stormshield_services import (
    check_stormshield_services,
    discover_stormshield_services,
    StormshieldService,
)

SECTION = {
    "one": StormshieldService("1", 42),
    "two": StormshieldService("0", 42),
}


def test_discover() -> None:
    assert list(discover_stormshield_services(SECTION)) == [Service(item="one")]


def test_check_up() -> None:
    assert list(check_stormshield_services(item="one", section=SECTION)) == [
        Result(state=State.OK, summary="Up"),
        Result(state=State.OK, summary="Uptime: 42 seconds"),
        Metric("uptime", 42.0),
    ]


def test_check_down() -> None:
    assert list(check_stormshield_services(item="two", section=SECTION)) == [
        Result(state=State.WARN, summary="Down"),
    ]

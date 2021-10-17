#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple

import pytest

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

from tests.unit.conftest import FixRegister


class StormshieldService(NamedTuple):
    state: str
    uptime: int


SECTION = {
    "one": StormshieldService("1", 42),
    "two": StormshieldService("0", 42),
}


@pytest.fixture(scope="module", name="stormshield_services")
def _stormshield_services(fix_register: FixRegister):
    return fix_register.check_plugins[CheckPluginName("stormshield_services")]


def test_discover(stormshield_services) -> None:
    assert list(stormshield_services.discovery_function(SECTION)) == [Service(item="one")]


def test_check_up(stormshield_services) -> None:
    assert list(stormshield_services.check_function(item="one", params={}, section=SECTION)) == [
        Result(state=State.OK, summary="Up"),
        Result(state=State.OK, summary="Uptime: 42.0 s"),
        Metric("uptime", 42.0),
    ]


def test_check_down(stormshield_services) -> None:
    assert list(stormshield_services.check_function(item="two", params={}, section=SECTION)) == [
        Result(state=State.WARN, summary="Down"),
    ]

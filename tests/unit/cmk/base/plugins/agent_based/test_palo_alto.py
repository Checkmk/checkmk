#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State


def test_inventory_palo_alto(fix_register: FixRegister) -> None:
    info = [["5.0.6", "disabled", "unknown", "disabled"]]
    check_plugin = fix_register.check_plugins[CheckPluginName("palo_alto")]
    assert list(check_plugin.discovery_function(info)) == [Service()]


def test_check_palo_alto(fix_register: FixRegister) -> None:
    info = [["5.0.6", "disabled", "unknown", "disabled"]]
    check_plugin = fix_register.check_plugins[CheckPluginName("palo_alto")]
    assert list(check_plugin.check_function(item=None, params={}, section=info)) == [
        Result(state=State.OK, summary="Firmware Version: 5.0.6"),
        Result(state=State.OK, summary="HA mode: disabled"),
        Result(state=State.OK, summary="Local HA state: disabled"),
        Result(state=State.OK, summary="Peer HA state: unknown"),
    ]

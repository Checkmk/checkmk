#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, Dict, Tuple, List

import pytest  # type: ignore[import]

from cmk.utils.type_defs import CheckPluginName, SectionName
import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.api.agent_based.type_defs import SNMPSectionPlugin, StringTable
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State

# raw data looks like this:
# TODO: we sould use this as test input
# ## AIRESPACE-WIRELESS-MIB::bsnDot11EssSsid
# .1.3.6.1.4.1.14179.2.1.1.1.2.2 corp_internal_001
# .1.3.6.1.4.1.14179.2.1.1.1.2.3 corp_internal_003
# .1.3.6.1.4.1.14179.2.1.1.1.2.19 AnotherWifiSSID
# .1.3.6.1.4.1.14179.2.1.1.1.2.31 FreePublicWifi
# .1.3.6.1.4.1.14179.2.1.1.1.2.32 FreePublicWifi
# .1.3.6.1.4.1.14179.2.1.1.1.2.33 FreePublicWifi
# ## AIRESPACE-WIRELESS-MIB::bsnDot11EssInterfaceName
# .1.3.6.1.4.1.14179.2.1.1.1.42.2 corp_intern_001
# .1.3.6.1.4.1.14179.2.1.1.1.42.3 corp_intern_003
# .1.3.6.1.4.1.14179.2.1.1.1.42.19 interface_name
# .1.3.6.1.4.1.14179.2.1.1.1.42.31 guest1
# .1.3.6.1.4.1.14179.2.1.1.1.42.32 guest2
# .1.3.6.1.4.1.14179.2.1.1.1.42.33 guest3
# ## AIRESPACE-WIRELESS-MIB::bsnDot11EssNumberOfMobileStations
# .1.3.6.1.4.1.14179.2.1.1.1.38.2 1
# .1.3.6.1.4.1.14179.2.1.1.1.38.3 3
# .1.3.6.1.4.1.14179.2.1.1.1.38.19 0
# .1.3.6.1.4.1.14179.2.1.1.1.38.31 0
# .1.3.6.1.4.1.14179.2.1.1.1.38.32 114
# .1.3.6.1.4.1.14179.2.1.1.1.38.33 68

INFO = [[
    ["corp_internal_001", "corp_intern_001", "1"],
    ["corp_internal_003", "corp_intern_003", "3"],
    ["AnotherWifiSSID", "interface_name", "0"],
    ["FreePublicWifi", "guest1", "0"],
    ["FreePublicWifi", "guest2", "114"],
    ["FreePublicWifi", "guest3", "68"],
]]

ITEM_RESULT = [
    [
        "Summary",
        [
            Result(state=State.OK, summary='186 connections'),
            Metric('connections', 186.0),
        ],
    ],
    [
        "corp_internal_003",
        [
            Result(state=State.OK, summary='3 connections (corp_intern_003: 3)'),
            Metric('connections', 3.0),
        ],
    ],
    [
        "FreePublicWifi",
        [
            Result(state=State.OK, summary='182 connections (guest1: 0, guest2: 114, guest3: 68)'),
            Metric('connections', 182.0),
        ],
    ],
]


@pytest.mark.usefixtures("load_all_agent_based_plugins")
def _run_parse_and_check(
    item: str,
    info: List[StringTable],
    params: Optional[Dict[str, Tuple[float, float]]] = None,
):
    if params is None:
        params = {}
    section = agent_based_register.get_snmp_section_plugin(SectionName('cisco_wlc_clients'))
    assert isinstance(section, SNMPSectionPlugin)
    plugin = agent_based_register.get_check_plugin(CheckPluginName('cisco_wlc_clients'))
    assert plugin
    result = list(
        plugin.check_function(
            item=item,
            params=params,
            section=section.parse_function(info),  # type: ignore[arg-type]
        ))
    return result


@pytest.mark.parametrize("item, result", ITEM_RESULT)
@pytest.mark.usefixtures("load_all_agent_based_plugins")
def test_cisco_wlc_clients(item, result):
    assert _run_parse_and_check(item, INFO) == result


PARAM_STATUS = [
    # summary: 186 connections
    [dict(), State.OK],
    [dict(levels=(300, 400)), State.OK],
    [dict(levels=(100, 400)), State.WARN],
    [dict(levels=(50, 100)), State.CRIT],
    [dict(levels_lower=(100, 50)), State.OK],
    [dict(levels_lower=(200, 100)), State.WARN],
    [dict(levels_lower=(300, 200)), State.CRIT],
    # check status when exactly on the defined level
    [dict(levels=(186, 400)), State.WARN],
    [dict(levels=(50, 186)), State.CRIT],
    [dict(levels_lower=(186, 100)), State.OK],
    [dict(levels_lower=(300, 186)), State.WARN],
]


@pytest.mark.parametrize("param, status", PARAM_STATUS)
@pytest.mark.usefixtures("load_all_agent_based_plugins")
def test_cisco_wlc_clients_parameter(param, status):
    result = _run_parse_and_check('Summary', INFO, param)
    assert result[0].state == status

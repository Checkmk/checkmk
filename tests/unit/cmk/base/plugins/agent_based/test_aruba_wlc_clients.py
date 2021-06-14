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
# TODO: we should use this as test input
# .1.3.6.1.4.1.14823.2.2.1.5.2.1.8.1.2.0 0 --> WLSX-WLAN-MIB::wlanESSIDNumStations.""
# .1.3.6.1.4.1.14823.2.2.1.5.2.1.8.1.2.4.86.111.73.80 0 --> WLSX-WLAN-MIB::wlanESSIDNumStations."VoIP"
# .1.3.6.1.4.1.14823.2.2.1.5.2.1.8.1.2.5.87.105.76.65.78 37 --> WLSX-WLAN-MIB::wlanESSIDNumStations."WiLAN"
# .1.3.6.1.4.1.14823.2.2.1.5.2.1.8.1.2.7.77.45.87.105.76.65.78 44 --> WLSX-WLAN-MIB::wlanESSIDNumStations."M-WiLAN"

INFO: List[StringTable] = [[
    ["0", "0"],
    ["4.86.111.73.80", "0"],
    ["5.87.105.76.65.78", "37"],
    ["7.77.45.87.105.76.65.78", "44"],
]]

ITEM_RESULT = [
    [
        "Summary",
        [
            Result(state=State.OK, summary='81 connections'),
            Metric('connections', 81.0),
        ],
    ],
    [
        "VoIP",
        [
            Result(state=State.OK, summary='0 connections'),
            Metric('connections', 0.0),
        ],
    ],
    [
        "WiLAN",
        [
            Result(state=State.OK, summary='37 connections'),
            Metric('connections', 37.0),
        ],
    ],
]


def _run_parse_and_check(
    item: str,
    info: List[StringTable],
    params: Optional[Dict[str, Tuple[float, float]]] = None,
):
    if params is None:
        params = {}
    section = agent_based_register.get_snmp_section_plugin(SectionName('aruba_wlc_clients'))
    assert isinstance(section, SNMPSectionPlugin)
    plugin = agent_based_register.get_check_plugin(CheckPluginName('aruba_wlc_clients'))
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
def test_aruba_wlc_clients(item, result):
    assert _run_parse_and_check(item, INFO) == result


@pytest.mark.usefixtures("load_all_agent_based_plugins")
def test_parse_aruba_wlc_clients():
    section = agent_based_register.get_snmp_section_plugin(SectionName('aruba_wlc_clients'))
    assert section
    result = section.parse_function(INFO)  # type: ignore[arg-type]
    assert result == {
        "Summary": (81, ""),
        "VoIP": (0, ""),
        "WiLAN": (37, ""),
        "M-WiLAN": (44, ""),
    }

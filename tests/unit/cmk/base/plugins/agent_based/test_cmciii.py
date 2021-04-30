#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.utils.type_defs import CheckPluginName, SectionName
import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State


def _leakage_info(status, position):
    return "CMCIII-LEAK Leakage", [
        [['4', 'CMCIII-LEAK', 'CMCIII-LEAK', '2']],
        [
            ['4.1', 'Leakage.DescName', '1', '', '0', 'Leakage', '0'],
            ['4.2', 'Leakage.Position', '33', '', '0', position, '0'],
            ['4.3', 'Leakage.Delay', '21', 's', '1', '1 s', '1'],
            ['4.4', 'Leakage.Status', '7', '', '0', status, '4'],
            ['4.5', 'Leakage.Category', '14', '', '0', '0', '0'],
        ],
    ]


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize('status, position, expected', [
    (
        'OK',
        'None',
        [
            Result(state=State.OK, summary='Status: OK'),
            Result(state=State.OK, summary='Delay: 1 s'),
        ],
    ),
    (
        'ProbeOpen',
        'None',
        [
            Result(state=State.CRIT, summary='Status: ProbeOpen'),
            Result(state=State.OK, summary='Delay: 1 s'),
        ],
    ),
    (
        'Alarm',
        'Zone 1',
        [
            Result(state=State.CRIT, summary='Status: Alarm'),
            Result(state=State.OK, summary='Delay: 1 s'),
        ],
    ),
])
def test_cmciii_leakage_sensors(status, position, expected):
    section_plugin = agent_based_register.get_section_plugin(SectionName('cmciii'))
    assert section_plugin
    plugin = agent_based_register.get_check_plugin(CheckPluginName('cmciii_leakage'))
    assert plugin

    item, info = _leakage_info(status, position)
    section = section_plugin.parse_function(info)
    assert list(plugin.check_function(item=item, params={}, section=section)) == expected

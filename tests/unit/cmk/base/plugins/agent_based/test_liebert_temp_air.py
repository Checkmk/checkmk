#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.liebert_temp_air import (
    parse_liebert_temp_air,
    discover_liebert_temp_air,
    check_liebert_temp_air,
)
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Result,
    State as state,
    Service,
    Metric,
)

STRING_TABLE = [[[
    'Return Air Temperature',
    '107.6',
    'deg F',
    'Some made-up Air Temperature',
    'Unavailable',
    'deg C',
]]]

PARAMETERS = {
    'levels': (50, 55),
    'levels_lower': (10, 15),
}

PARSED_SECTION = {
    'Return Air Temperature': ['107.6', 'deg F'],
    'Some made-up Air Temperature': ['Unavailable', 'deg C'],
}

PARSED_EXTRA_SECTION = {
    'System Model Number': 'Liebert CRV',
    'System Status': 'Normal Operation',
    'Unit Operating State': 'standby',
    'Unit Operating State Reason': 'Reason Unknown',
}


@pytest.mark.parametrize('string_table, result', [
    (
        STRING_TABLE,
        PARSED_SECTION,
    ),
])
def test_parse_liebert_temp_air(string_table, result):
    parsed = parse_liebert_temp_air(string_table)
    assert parsed == result


@pytest.mark.parametrize('section, extra_section, result', [(
    PARSED_SECTION,
    PARSED_EXTRA_SECTION,
    [Service(item='Return')],
)])
def test_discover_liebert_temp_air(section, extra_section, result):
    discovered = list(discover_liebert_temp_air(section, extra_section))
    assert discovered == result


@pytest.mark.parametrize(
    'item, params, section, extra_section, result',
    [
        (
            'Return',
            PARAMETERS,
            PARSED_SECTION,
            PARSED_EXTRA_SECTION,
            [
                Metric(name='temp', value=42.0, levels=(50.0, 55.0), boundaries=(None, None)),
                Result(state=state.OK, summary='Temperature: 42.0°C'),
                Result(
                    state=state.OK,
                    notice='Configuration: prefer user levels over device levels (used user levels)',
                ),
            ],
        ),
        (
            # Item 'Some made-up' is not discovered in the discovery function. However, it is tested in this check function
            # in order to test whether the check handles the item correctly when it changes its status from 'on' to
            # 'standby'.
            'Some made-up',
            PARAMETERS,
            PARSED_SECTION,
            PARSED_EXTRA_SECTION,
            [
                Result(state=state.OK, summary='Unit is in standby (unavailable)'),
            ],
        ),
    ])
def test_check_liebert_temp_air(item, params, section, extra_section, result):
    checked = list(check_liebert_temp_air(item, params, section, extra_section))
    assert checked == result

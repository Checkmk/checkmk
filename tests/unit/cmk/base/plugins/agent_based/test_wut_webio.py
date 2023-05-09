#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.agent_based_api.v1 import Service, State, Result
from cmk.base.plugins.agent_based.wut_webio import (
    parse_wut_webio,
    check_wut_webio,
    discover_wut_webio,
    Section,
    STATES_DURING_DISC_KEY,
    STATE_EVAL_KEY,
    AS_DISCOVERED,
    DEFAULT_STATE_EVALUATION,
)

STRING_TABLE = [
    [],
    [['WEBIO-094849', '', '', ''], ['', '1', 'Input 0', '1'], ['', '2', 'Input 1', '0']],
    [],
]

ITEM = "WEBIO-094849 Input 0"


def _parse_mandatory(string_table) -> Section:
    section = parse_wut_webio(string_table)
    assert section
    return section


def test_discovery():
    assert list(discover_wut_webio(_parse_mandatory(STRING_TABLE))) == [
        Service(item=ITEM, parameters={'states_during_discovery': 'On'}),
        Service(item='WEBIO-094849 Input 1', parameters={'states_during_discovery': 'Off'})
    ]


@pytest.mark.parametrize(
    "params, expected",
    [
        ({
            STATE_EVAL_KEY: DEFAULT_STATE_EVALUATION,
            STATES_DURING_DISC_KEY: "Off"
        }, [Result(state=State.OK, summary='Input (Index: 1) is in state: On')]),
        ({
            STATE_EVAL_KEY: AS_DISCOVERED,
            STATES_DURING_DISC_KEY: "Off"
        }, [Result(state=State.CRIT, summary='Input (Index: 1) is in state: On')]),
    ],
)
def test_check(params, expected):
    assert list(check_wut_webio(ITEM, params, _parse_mandatory(STRING_TABLE))) == expected

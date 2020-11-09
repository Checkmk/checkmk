#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import Parameters
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State as state
from cmk.base.plugins.agent_based.mssql_databases import (
    parse_mssql_databases,
    discover_mssql_databases,
    check_mssql_databases,
)


@pytest.fixture(scope="module", name="section")
def _get_section():
    return parse_mssql_databases([
        ['MSSQL_MSSQL46', 'CorreLog_Report_T', 'ONLINE', 'FULL', '0', '0'],
        ['MSSQL_MSSQL46', 'master', 'ONLINE', 'SIMPLE', '0', '0'],
        ['MSSQL_MSSQL46', 'msdb', 'ONLINE', 'SIMPLE', '0', '0'],
        ['MSSQL_MSSQL46', 'NOC_ALARM_T', 'ONLINE', 'FULL', '0', '1'],
        ['MSSQL_MSSQL46', 'test_autoclose', 'ONLINE', 'FULL', '1', '0'],
        ['MSSQL_MSSQL46', 'test_autoclose', 'RECOVERY', 'PENDING', 'FULL', '1', '0'],
        ['MSSQL_Mouse', '-', 'ERROR: We are out of cheese!', '-', '-', '-'],
    ])


def test_discover_mssql_databases(section):

    assert sorted(discover_mssql_databases(section),
                  key=lambda s: s.item or "") == [  # type: ignore[attr-defined]
                      Service(item='MSSQL_MSSQL46 CorreLog_Report_T'),
                      Service(item='MSSQL_MSSQL46 NOC_ALARM_T'),
                      Service(item='MSSQL_MSSQL46 master'),
                      Service(item='MSSQL_MSSQL46 msdb'),
                      Service(item='MSSQL_MSSQL46 test_autoclose'),
                      Service(item='MSSQL_Mouse -'),
                  ]


def test_check_error(section):

    assert list(check_mssql_databases("MSSQL_Mouse -", Parameters({}), section)) == [
        Result(state=state.CRIT, summary="We are out of cheese!"),
    ]


def test_check_warn_auto_shrink(section):

    assert list(check_mssql_databases("MSSQL_MSSQL46 NOC_ALARM_T", Parameters({}), section)) == [
        Result(state=state.OK, summary="Status: ONLINE"),
        Result(state=state.OK, summary="Recovery: FULL"),
        Result(state=state.OK, summary="Auto close: off"),
        Result(state=state.WARN, summary="Auto shrink: on"),
    ]

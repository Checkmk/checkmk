#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import Parameters
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Service, Result, State as state
import cmk.base.plugins.agent_based.mssql_datafiles_transactionlogs as msdt
import cmk.base.plugins.agent_based.mssql_databases as msdb


@pytest.fixture(name="section", scope="module")
def _get_section():
    return msdt.parse_mssql_datafiles(
        [[
            'MSSQL46', 'CorreLog_Report_T', 'CorreLog_Report_T_log',
            'Z:\\mypath\\CorreLog_Report_T_log.ldf', '2097152', '256', '16', '0'
        ],
         [
             'MSSQL46', 'DASH_CONFIG_T', 'DASH_CONFIG_T_log', 'Z:\\mypath\\DASH_CONFIG_T_log.ldf',
             '2097152', '256', '1', '0'
         ], ['MSSQL46', 'master', 'mastlog', 'Z:\\mypath\\mastlog.ldf', '0', '1', '0', '1'],
         ['MSSQL46', 'model', 'modellog', 'Z:\\mypath\\modellog.ldf', '0', '34', '32', '1'],
         ['MSSQL46', 'msdb', 'MSDBLog', 'Z:\\mypath\\MSDBLog.ldf', '2097152', '17', '3', '0'],
         [
             'MSSQL46', 'NOC_ALARM_T', 'NOC_ALARM_T_log', 'Z:\\mypath\\NOC_ALARM_T_log.ldf',
             '2097152', '256', '8', '0'
         ],
         [
             'MSSQL46', 'NOC_CONFIG_T', 'NOC_CONFIG_T_log', 'Z:\\mypath\\NOC_CONFIG_T_log.ldf',
             '2097152', '768', '31', '0'
         ], ['MSSQL46', 'tempdb', 'templog', 'Z:\\mypath\\templog.ldf', '0', '160', '55', '1'],
         [
             'MSSQL46', 'test_autoclose', 'test_autoclose_log',
             'Z:\\mypath\\test_autoclose_log.ldf', '2097152', '32', '1', '0'
         ]])


def test_discovery_mssql_transactionlogs(section):

    section_db = msdb.parse_mssql_databases([
        ['MSSQL46', 'master', 'ONLINE', 'SIMPLE', '0', '0'],
        ['MSSQL46', 'tempdb', 'ONLINE', 'SIMPLE', '0', '0'],
        ['MSSQL46', 'model', 'ONLINE', 'FULL', '0', '0'],
        ['MSSQL46', 'msdb', 'ONLINE', 'SIMPLE', '0', '0'],
        ['MSSQL46', 'NOC_CONFIG_T', 'ONLINE', 'FULL', '0', '0'],
        ['MSSQL46', 'DASH_CONFIG_T', 'ONLINE', 'FULL', '0', '0'],
        ['MSSQL46', 'NOC_ALARM_T', 'ONLINE', 'FULL', '0', '1'],
        ['MSSQL46', 'CorreLog_Report_T', 'ONLINE', 'FULL', '0', '0'],
        ['MSSQL46', 'test_autoclose', 'ONLINE', 'FULL', '1', '0'],
    ])

    assert sorted(
        msdt.discover_mssql_transactionlogs([Parameters({})], section, section_db),
        key=lambda s: s.item,  # type: ignore[attr-defined]
    ) == [
        Service(item='MSSQL46.CorreLog_Report_T.CorreLog_Report_T_log'),
        Service(item='MSSQL46.DASH_CONFIG_T.DASH_CONFIG_T_log'),
        Service(item='MSSQL46.NOC_ALARM_T.NOC_ALARM_T_log'),
        Service(item='MSSQL46.NOC_CONFIG_T.NOC_CONFIG_T_log'),
        Service(item='MSSQL46.model.modellog'),
        Service(item='MSSQL46.test_autoclose.test_autoclose_log'),
    ]


def test_check_mssql_transactionlogs(section):
    assert list(
        msdt.check_mssql_transactionlogs(
            'MSSQL46.CorreLog_Report_T.CorreLog_Report_T_log',
            Parameters({}),
            section,
            None,
        ),) == [
            Result(
                state=state.OK,
                summary='Used: 16.0 MiB',
            ),
            Metric('data_size', 16777216.0, boundaries=(0, 2199023255552.0)),
            Result(
                state=state.OK,
                summary='Allocated used: 16.0 MiB',
            ),
            Result(
                state=state.OK,
                summary='Allocated: 256 MiB',
            ),
            Metric('allocated_size', 268435456.0, boundaries=(0, 2199023255552.0)),
            Result(
                state=state.OK,
                summary="Maximum size: 2.00 TiB",
            ),
        ]
